# Generated manually — proxy model for aggregated stock view

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('inventory', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='StockCourantProxy',
            fields=[
            ],
            options={
                'verbose_name': 'Stock actuel (tous dépôts)',
                'verbose_name_plural': 'Stock actuel (tous dépôts)',
                'proxy': True,
                'indexes': [],
                'constraints': [],
            },
            bases=('inventory.stockcourant',),
        ),
    ]
