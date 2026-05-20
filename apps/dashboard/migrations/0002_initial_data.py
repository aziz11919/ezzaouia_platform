from django.db import migrations


def create_prototype_report(apps, schema_editor):
    PowerBIReport = apps.get_model('dashboard', 'PowerBIReport')
    PowerBIReport.objects.get_or_create(
        title='prototype',
        defaults={
            'embed_url': (
                'https://app.powerbi.com/reportEmbed'
                '?reportId=f98f0f03-2b1c-4317-a688-116429e02368'
                '&autoAuth=true'
                '&ctid=e5566d93-938b-4399-8fcb-42625d61a161'
                '&navContentPaneEnabled=true'
            ),
            'icon':   '📊',
            'role':   'all',
            'active': True,
            'order':  0,
        },
    )


class Migration(migrations.Migration):

    dependencies = [
        ('dashboard', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(create_prototype_report, migrations.RunPython.noop),
    ]
