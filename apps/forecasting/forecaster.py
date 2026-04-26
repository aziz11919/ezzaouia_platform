import math
import pandas as pd
import numpy as np
import warnings
warnings.filterwarnings('ignore')

from django.db import connection
import logging

logger = logging.getLogger('apps')

# Optional model dependencies: keep module import-safe so Celery can boot even
# when one forecasting backend is not installed in the current image.
try:
    from prophet import Prophet
except Exception:
    Prophet = None

try:
    from statsmodels.tsa.holtwinters import ExponentialSmoothing
    from statsmodels.tsa.stattools import adfuller
    from statsmodels.tsa.seasonal import seasonal_decompose
except Exception:
    ExponentialSmoothing = None
    adfuller = None
    seasonal_decompose = None

try:
    from pmdarima import auto_arima
except Exception:
    auto_arima = None

try:
    from sklearn.metrics import mean_absolute_error, mean_squared_error
except Exception:
    mean_absolute_error = None
    mean_squared_error = None


# ─── Serialization helpers ────────────────────────────────────────────────────

def safe_val(val):
    """Convert any numeric to a plain Python float; returns 0.0 on NaN/Inf/None."""
    try:
        if val is None:
            return 0.0
        v = float(val)
        if math.isnan(v) or math.isinf(v):
            return 0.0
        return round(v, 2)
    except Exception:
        return 0.0


def safe_int(val):
    """Convert any integer-like value to a plain Python int."""
    try:
        return int(val)
    except Exception:
        return 0


# ─── Data fetching ────────────────────────────────────────────────────────────

def get_monthly_production(well_key=None, kpi='oil'):
    """
    Fetch monthly aggregated production from SQL Server DWH.
    Returns DataFrame with columns: ds (date), y (value)

    kpi options: 'oil' (BOPD), 'bsw', 'gor', 'water', 'gas', 'prodhours'
    """
    kpi_map = {
        'oil':       'SUM(f.DailyOilPerWellSTBD)',
        'gas':       'SUM(f.DailyGasPerWellMSCF)',
        'water':     'SUM(f.WellStatusWaterBWPD)',
        'bsw':       'AVG(CAST(ws.BSW AS FLOAT))',
        'gor':       'AVG(CAST(ws.GOR AS FLOAT))',
        'prodhours': 'AVG(CAST(ws.ProdHours AS FLOAT))',
    }

    agg_expr = kpi_map.get(kpi, kpi_map['oil'])
    well_filter = f"AND f.WellKey = {int(well_key)}" if well_key else ""

    sql = f"""
        SELECT
            DATEFROMPARTS(d.[Year], d.[Month], 1) AS month_date,
            {agg_expr} AS value
        FROM dbo.FactProduction f
        JOIN dbo.DimDate d ON f.DateKey = d.DateKey
        LEFT JOIN dbo.DimWellStatus ws ON f.WellStatusKey = ws.WellStatusKey
        WHERE f.DailyOilPerWellSTBD >= 0
        {well_filter}
        GROUP BY d.[Year], d.[Month]
        ORDER BY d.[Year], d.[Month]
    """

    with connection.cursor() as c:
        c.execute(sql)
        rows = c.fetchall()

    if not rows:
        return pd.DataFrame()

    df = pd.DataFrame(rows, columns=['ds', 'y'])
    df['ds'] = pd.to_datetime(df['ds'])
    df['y'] = pd.to_numeric(df['y'], errors='coerce').fillna(0)
    return df


# ─── Statistical analysis ─────────────────────────────────────────────────────

def test_stationarity(series):
    """ADF test for stationarity."""
    try:
        if adfuller is None:
            return {'error': 'statsmodels is not installed'}
        result = adfuller(series.dropna())
        return {
            'adf_stat': round(float(result[0]), 4),
            'p_value': round(float(result[1]), 4),
            'is_stationary': bool(result[1] < 0.05),
            'critical_values': {k: round(float(v), 4) for k, v in result[4].items()},
        }
    except Exception as e:
        return {'error': str(e)}


_MONTH_NAMES = {
    1: 'January', 2: 'February', 3: 'March', 4: 'April',
    5: 'May', 6: 'June', 7: 'July', 8: 'August',
    9: 'September', 10: 'October', 11: 'November', 12: 'December',
}


def detect_seasonality(df):
    """
    Detect yearly seasonality using additive decomposition + ACF lag-12.
    Additive model is more robust than multiplicative when zeros are present.
    Detection fires if EITHER decomposition strength > 0.05 OR ACF lag-12 > 0.3.
    """
    try:
        from statsmodels.tsa.stattools import acf as _acf

        if len(df) < 24:
            return {'detected': False, 'reason': 'Insufficient data'}

        series = df.set_index('ds')['y'].resample('MS').mean()
        series = series.fillna(series.median())
        series = series.clip(lower=0.01)   # avoid multiplicative divide-by-zero

        # Additive decomposition (more robust for declining production series)
        decomp = None
        strength = 0.0
        try:
            decomp = seasonal_decompose(
                series,
                model='additive',
                period=12,
                extrapolate_trend='freq',
            )
            residual = decomp.resid.dropna()
            seasonal = decomp.seasonal

            var_residual = float(residual.var())
            var_seasonal_residual = float((seasonal + residual).var())

            if var_seasonal_residual > 0:
                strength = max(0.0, 1.0 - var_residual / var_seasonal_residual)
        except Exception:
            pass

        # ACF check: annual peak at lag 12
        seasonal_acf = 0.0
        try:
            acf_values = _acf(series.values, nlags=24, fft=True)
            seasonal_acf = safe_val(abs(acf_values[12]))
        except Exception:
            pass

        detected = bool(strength > 0.05 or seasonal_acf > 0.3)

        # Per-month production averages to find peak / low months
        monthly_avg = df.copy()
        monthly_avg['month'] = monthly_avg['ds'].dt.month
        monthly_means = monthly_avg.groupby('month')['y'].mean()
        peak_month = int(monthly_means.idxmax())
        low_month = int(monthly_means.idxmin())

        # Trend direction from decomposition or raw series fallback
        if decomp is not None:
            trend_vals = decomp.trend.dropna().values
        else:
            trend_vals = series.values
        trend_direction = 'declining' if float(trend_vals[-1]) < float(trend_vals[0]) else 'increasing'

        return {
            'detected': detected,
            'strength': safe_val(strength),
            'acf_lag12': safe_val(seasonal_acf),
            'period': 12,
            'interpretation': (
                'Strong' if strength > 0.4 else
                'Moderate' if strength > 0.15 else
                'Weak' if detected else
                'Not detected'
            ),
            'peak_month': peak_month,
            'peak_month_name': _MONTH_NAMES.get(peak_month, ''),
            'low_month': low_month,
            'low_month_name': _MONTH_NAMES.get(low_month, ''),
            'trend_direction': trend_direction,
            'monthly_averages': {str(k): safe_val(v) for k, v in monthly_means.items()},
        }

    except Exception as e:
        logger.error(f"Seasonality error: {e}")
        return {'detected': False, 'error': str(e), 'interpretation': 'Error during analysis'}


# ─── Forecasting models ───────────────────────────────────────────────────────

def run_prophet(df, periods=60, changepoint_scale=0.05):
    """Run Facebook Prophet model. periods = months to forecast (default 60 = 5 years)."""
    try:
        if Prophet is None:
            logger.warning("Prophet package is not installed; skipping Prophet model")
            return None
        if mean_absolute_error is None or mean_squared_error is None:
            logger.warning("scikit-learn is not installed; skipping Prophet model")
            return None
        if len(df) < 24:
            logger.warning(f"Prophet: not enough data ({len(df)} rows)")
            return None

        split = max(12, int(len(df) * 0.8))
        if split >= len(df):
            split = len(df) - 6
        if split <= 0 or (len(df) - split) < 1:
            return None

        train = df.iloc[:split].copy()
        test = df.iloc[split:].copy()
        if len(test) == 0:
            return None

        model = Prophet(
            changepoint_prior_scale=changepoint_scale,
            seasonality_mode='multiplicative',
            yearly_seasonality=True,
            weekly_seasonality=False,
            daily_seasonality=False,
            interval_width=0.95,
        )
        model.fit(train)

        test_forecast = model.predict(test[['ds']])
        mae = safe_val(mean_absolute_error(test['y'], test_forecast['yhat']))
        rmse = safe_val(np.sqrt(mean_squared_error(test['y'], test_forecast['yhat'])))
        mape = safe_val(
            np.mean(np.abs((test['y'].values - test_forecast['yhat'].values) / (test['y'].values + 1e-10))) * 100
        )

        future = model.make_future_dataframe(periods=periods, freq='MS')
        forecast = model.predict(future)

        forecast_future = forecast[forecast['ds'] > df['ds'].max()].copy()
        if forecast_future.empty:
            return None

        forecast_future['quarter'] = forecast_future['ds'].dt.quarter
        forecast_future['year'] = forecast_future['ds'].dt.year

        quarterly = forecast_future.groupby(['year', 'quarter'])['yhat'].sum().reset_index()
        quarterly_list = [
            {
                'year': safe_int(row['year']),
                'quarter': safe_int(row['quarter']),
                'yhat': safe_val(row['yhat']),
            }
            for _, row in quarterly.iterrows()
        ]

        future_vals = forecast_future['yhat'].values
        trend = 'declining' if len(future_vals) >= 2 and float(future_vals[-1]) < float(future_vals[0]) else 'increasing'

        return {
            'model': 'Prophet',
            'metrics': {'mae': mae, 'rmse': rmse, 'mape': mape},
            'forecast': [
                {
                    'date': row['ds'].strftime('%Y-%m-%d'),
                    'yhat': safe_val(max(0, row['yhat'])),
                    'yhat_lower': safe_val(max(0, row['yhat_lower'])),
                    'yhat_upper': safe_val(max(0, row['yhat_upper'])),
                }
                for _, row in forecast_future.iterrows()
            ],
            'quarterly': quarterly_list,
            'historical': [
                {'date': row['ds'].strftime('%Y-%m-%d'), 'value': safe_val(row['y'])}
                for _, row in df.iterrows()
            ],
            'trend_direction': trend,
        }
    except Exception as e:
        logger.error(f"Prophet error: {e}")
        return None


def run_sarima(df, periods=60):
    """Run SARIMA model with auto parameter selection."""
    try:
        if auto_arima is None:
            logger.warning("pmdarima package is not installed; skipping SARIMA model")
            return None
        if mean_absolute_error is None or mean_squared_error is None:
            logger.warning("scikit-learn is not installed; skipping SARIMA model")
            return None
        if len(df) < 24:
            return None

        split = max(12, int(len(df) * 0.8))
        if split >= len(df):
            split = len(df) - 6
        train = df.iloc[:split]['y'].values
        test = df.iloc[split:]['y'].values
        if len(test) == 0:
            return None

        model = auto_arima(
            train,
            seasonal=True,
            m=12,
            stepwise=True,
            suppress_warnings=True,
            error_action='ignore',
            max_p=3, max_q=3,
            max_P=2, max_Q=2,
        )

        test_pred = model.predict(n_periods=len(test))
        mae = safe_val(mean_absolute_error(test, test_pred))
        rmse = safe_val(np.sqrt(mean_squared_error(test, test_pred)))
        mape = safe_val(np.mean(np.abs((test - test_pred) / (test + 1e-10))) * 100)

        forecast_values, conf_int = model.predict(n_periods=periods, return_conf_int=True)

        last_date = df['ds'].max()
        future_dates = pd.date_range(start=last_date + pd.DateOffset(months=1), periods=periods, freq='MS')

        forecast_df = pd.DataFrame({
            'date': future_dates,
            'yhat': np.maximum(0, forecast_values),
            'yhat_lower': np.maximum(0, conf_int[:, 0]),
            'yhat_upper': np.maximum(0, conf_int[:, 1]),
        })

        forecast_df['quarter'] = forecast_df['date'].dt.quarter
        forecast_df['year'] = forecast_df['date'].dt.year
        quarterly = forecast_df.groupby(['year', 'quarter'])['yhat'].sum().reset_index()
        quarterly_list = [
            {
                'year': safe_int(row['year']),
                'quarter': safe_int(row['quarter']),
                'yhat': safe_val(row['yhat']),
            }
            for _, row in quarterly.iterrows()
        ]

        order = model.order
        seasonal_order = model.seasonal_order

        return {
            'model': 'SARIMA',
            'order': f"({order[0]},{order[1]},{order[2]})({seasonal_order[0]},{seasonal_order[1]},{seasonal_order[2]})[{seasonal_order[3]}]",
            'metrics': {'mae': mae, 'rmse': rmse, 'mape': mape},
            'forecast': [
                {
                    'date': row['date'].strftime('%Y-%m-%d'),
                    'yhat': safe_val(row['yhat']),
                    'yhat_lower': safe_val(row['yhat_lower']),
                    'yhat_upper': safe_val(row['yhat_upper']),
                }
                for _, row in forecast_df.iterrows()
            ],
            'quarterly': quarterly_list,
        }
    except Exception as e:
        logger.error(f"SARIMA error: {e}")
        return None


def run_arima(df, periods=60):
    """Run basic ARIMA as non-seasonal baseline."""
    try:
        if auto_arima is None:
            logger.warning("pmdarima package is not installed; skipping ARIMA model")
            return None
        if mean_absolute_error is None or mean_squared_error is None:
            logger.warning("scikit-learn is not installed; skipping ARIMA model")
            return None
        if len(df) < 12:
            return None

        split = max(12, int(len(df) * 0.8))
        if split >= len(df):
            split = len(df) - 6
        train = df.iloc[:split]['y'].values
        test = df.iloc[split:]['y'].values
        if len(test) == 0:
            return None

        model = auto_arima(
            train,
            seasonal=False,
            stepwise=True,
            suppress_warnings=True,
            error_action='ignore',
            max_p=3, max_q=3,
        )

        test_pred = model.predict(n_periods=len(test))
        mae = safe_val(mean_absolute_error(test, test_pred))
        rmse = safe_val(np.sqrt(mean_squared_error(test, test_pred)))
        mape = safe_val(np.mean(np.abs((test - test_pred) / (test + 1e-10))) * 100)

        forecast_values, conf_int = model.predict(n_periods=periods, return_conf_int=True)
        last_date = df['ds'].max()
        future_dates = pd.date_range(start=last_date + pd.DateOffset(months=1), periods=periods, freq='MS')

        return {
            'model': 'ARIMA',
            'order': str(model.order),
            'metrics': {'mae': mae, 'rmse': rmse, 'mape': mape},
            'forecast': [
                {
                    'date': d.strftime('%Y-%m-%d'),
                    'yhat': safe_val(max(0, v)),
                    'yhat_lower': safe_val(max(0, c[0])),
                    'yhat_upper': safe_val(max(0, c[1])),
                }
                for d, v, c in zip(future_dates, forecast_values, conf_int)
            ],
        }
    except Exception as e:
        logger.error(f"ARIMA error: {e}")
        return None


def run_holt_winters(df, periods=60):
    """Run Holt-Winters Exponential Smoothing."""
    try:
        if ExponentialSmoothing is None:
            logger.warning("statsmodels package is not installed; skipping Holt-Winters model")
            return None
        if mean_absolute_error is None or mean_squared_error is None:
            logger.warning("scikit-learn is not installed; skipping Holt-Winters model")
            return None
        if len(df) < 24:
            return None

        split = max(12, int(len(df) * 0.8))
        if split >= len(df):
            split = len(df) - 6
        train = df.iloc[:split]['y'].values
        test = df.iloc[split:]['y'].values
        if len(test) == 0:
            return None

        model = ExponentialSmoothing(
            train,
            trend='add',
            seasonal='add',
            seasonal_periods=12,
        ).fit(optimized=True)

        test_pred = model.forecast(len(test))
        mae = safe_val(mean_absolute_error(test, test_pred))
        rmse = safe_val(np.sqrt(mean_squared_error(test, test_pred)))
        mape = safe_val(np.mean(np.abs((test - test_pred) / (test + 1e-10))) * 100)

        forecast_values = model.forecast(periods)
        last_date = df['ds'].max()
        future_dates = pd.date_range(start=last_date + pd.DateOffset(months=1), periods=periods, freq='MS')

        return {
            'model': 'Holt-Winters',
            'metrics': {'mae': mae, 'rmse': rmse, 'mape': mape},
            'forecast': [
                {'date': d.strftime('%Y-%m-%d'), 'yhat': safe_val(max(0, v))}
                for d, v in zip(future_dates, forecast_values)
            ],
        }
    except Exception as e:
        logger.error(f"Holt-Winters error: {e}")
        return None


# ─── Main entry point ─────────────────────────────────────────────────────────

def run_all_models(well_key=None, kpi='oil', periods=60):
    """Run all 4 models and return comparison. Main API entry point."""
    df = get_monthly_production(well_key=well_key, kpi=kpi)

    if df.empty or len(df) < 12:
        return {'error': 'Insufficient data for forecasting'}

    stationarity = test_stationarity(df['y'])
    seasonality = detect_seasonality(df)

    results = {
        'well_key': well_key,
        'kpi': kpi,
        'periods': periods,
        'data_points': len(df),
        'date_range': {
            'start': df['ds'].min().strftime('%Y-%m-%d'),
            'end': df['ds'].max().strftime('%Y-%m-%d'),
        },
        'stationarity': stationarity,
        'seasonality': seasonality,
        'models': {},
    }

    for name, runner in [
        ('prophet',      lambda: run_prophet(df, periods)),
        ('sarima',       lambda: run_sarima(df, periods)),
        ('arima',        lambda: run_arima(df, periods)),
        ('holt_winters', lambda: run_holt_winters(df, periods)),
    ]:
        r = runner()
        if r:
            results['models'][name] = r

    valid_models = {k: v for k, v in results['models'].items() if v and 'metrics' in v}
    if valid_models:
        best_key = min(valid_models, key=lambda k: valid_models[k]['metrics']['mape'])
        results['best_model'] = best_key
        results['comparison'] = [
            {
                'model': v['model'],
                'mae': v['metrics']['mae'],
                'rmse': v['metrics']['rmse'],
                'mape': v['metrics']['mape'],
                'is_best': bool(k == best_key),
            }
            for k, v in valid_models.items()
        ]

    return results
