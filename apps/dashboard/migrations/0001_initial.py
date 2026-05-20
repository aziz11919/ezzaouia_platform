from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True
    dependencies = []

    operations = [
        migrations.CreateModel(
            name='PowerBIReport',
            fields=[
                ('id',          models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title',       models.CharField(max_length=200)),
                ('description', models.TextField(blank=True, default='')),
                ('embed_url',   models.URLField(max_length=2000)),
                ('icon',        models.CharField(default='📊', max_length=10)),
                ('role',        models.CharField(
                    choices=[('all', 'All roles'), ('admin', 'Admin only'), ('user', 'User')],
                    default='all',
                    max_length=20,
                )),
                ('order',      models.PositiveIntegerField(default=0)),
                ('active',     models.BooleanField(default=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
            ],
            options={
                'ordering': ['order', 'title'],
                'app_label': 'dashboard',
            },
        ),
    ]
