from django.db import migrations, models

class Migration(migrations.Migration):

    dependencies = [
        ('packages', '0009_remove_company_address_remove_company_email_and_more'),
    ]

    operations = [
        # Add fields back to Company model
        migrations.AddField(
            model_name='company',
            name='address',
            field=models.CharField(default='Company Address', max_length=255),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='company',
            name='email',
            field=models.EmailField(default='company@example.com', max_length=254),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='company',
            name='phone',
            field=models.CharField(default='0000000000', max_length=20),
            preserve_default=False,
        ),
        
        # Add missing fields to Driver
        migrations.AddField(
            model_name='driver',
            name='company',
            field=models.ForeignKey(default=1, on_delete=models.deletion.CASCADE, to='packages.company'),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='driver',
            name='phone',
            field=models.CharField(default='0000000000', max_length=20),
            preserve_default=False,
        ),
        
        # Add missing fields to Vehicle
        migrations.AddField(
            model_name='vehicle',
            name='company',
            field=models.ForeignKey(default=1, on_delete=models.deletion.CASCADE, to='packages.company'),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='vehicle',
            name='model',
            field=models.CharField(default='Unknown', max_length=100),
            preserve_default=False,
        ),
    ] 