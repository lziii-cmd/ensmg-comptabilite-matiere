from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('inventory', '0005_alter_mouvementstock_type_ficheaffectation'),
    ]

    operations = [
        migrations.CreateModel(
            name='SortieCertificatAdmin',
            fields=[
            ],
            options={
                'verbose_name': 'Sortie par certificat administratif',
                'verbose_name_plural': 'Sorties par certificat administratif',
                'proxy': True,
                'indexes': [],
                'constraints': [],
            },
            bases=('inventory.operationsortie',),
        ),
        migrations.CreateModel(
            name='SortieFinGestion',
            fields=[
            ],
            options={
                'verbose_name': 'Opération de fin de gestion',
                'verbose_name_plural': 'Opérations de fin de gestion',
                'proxy': True,
                'indexes': [],
                'constraints': [],
            },
            bases=('inventory.operationsortie',),
        ),
    ]
