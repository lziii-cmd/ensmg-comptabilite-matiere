from decimal import Decimal
from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ('catalog', '0001_initial'),
        ('core', '0001_initial'),
        ('purchasing', '0002_externalstockentry_externalstockentryline'),
    ]

    operations = [
        # ── Proxy model LegsEntry (même table qu'ExternalStockEntry) ──
        migrations.CreateModel(
            name='LegsEntry',
            fields=[],
            options={
                'verbose_name': 'Legs',
                'verbose_name_plural': 'Legs',
                'proxy': True,
                'indexes': [],
                'constraints': [],
            },
            bases=('purchasing.externalstockentry',),
        ),

        # ── Modèle Dotation (table propre, mouvement interne) ──
        migrations.CreateModel(
            name='Dotation',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('code', models.CharField(blank=True, default='', max_length=60, unique=True, verbose_name='Code')),
                ('date', models.DateField(default=django.utils.timezone.now, verbose_name='Date')),
                ('type_dotation', models.CharField(
                    choices=[
                        ('1ER_GROUPE',  '1er groupe — biens durables (affectation)'),
                        ('2EME_GROUPE', '2e groupe — consommables (sortie définitive)'),
                    ],
                    max_length=20,
                    verbose_name='Type de dotation',
                )),
                ('beneficiaire', models.CharField(max_length=200, verbose_name='Bénéficiaire (agent ou service)')),
                ('document_number', models.CharField(blank=True, default='', max_length=80, verbose_name='N° document (FIICM / bon de sortie)')),
                ('comment', models.TextField(blank=True, default='', verbose_name='Observations')),
                ('total_value', models.DecimalField(decimal_places=6, default=Decimal('0'), max_digits=16, verbose_name='Valeur totale')),
                ('depot', models.ForeignKey(
                    on_delete=django.db.models.deletion.PROTECT,
                    related_name='dotations',
                    to='core.depot',
                    verbose_name='Dépôt source',
                )),
            ],
            options={
                'verbose_name': 'Dotation',
                'verbose_name_plural': 'Dotations',
                'ordering': ['-date', '-id'],
            },
        ),

        # ── Lignes de dotation ──
        migrations.CreateModel(
            name='LigneDotation',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('quantity', models.DecimalField(decimal_places=3, max_digits=12, verbose_name='Quantité')),
                ('unit_price', models.DecimalField(decimal_places=4, default=Decimal('0'), max_digits=14, verbose_name='Prix unitaire')),
                ('total_ligne', models.DecimalField(decimal_places=4, default=Decimal('0'), max_digits=16, verbose_name='Total ligne')),
                ('note', models.CharField(blank=True, default='', max_length=200, verbose_name='Note')),
                ('dotation', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='lignes',
                    to='purchasing.dotation',
                )),
                ('matiere', models.ForeignKey(
                    on_delete=django.db.models.deletion.PROTECT,
                    to='catalog.matiere',
                    verbose_name='Matière',
                )),
            ],
            options={
                'verbose_name': 'Ligne de dotation',
                'verbose_name_plural': 'Lignes de dotation',
            },
        ),
    ]
