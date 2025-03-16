from django.db import models
import datetime
import pytz
from django.utils.timezone import now

GENDER_CHOICES = (
    ('M', 'Male'),
    ('F', 'Female'),
    ('O', 'Other'),
)

SOCIAL_ID_CHOICES = (
    ('google', 'Google'),
    ('facebook', 'Facebook'),
    ('twitter', 'Twitter'),
)

class Signer(models.Model):
    signature_counter = models.AutoField(primary_key=True)
    signer_full_name = models.CharField(max_length=255)
    gender = models.CharField(max_length=1, choices=GENDER_CHOICES)
    signer_father_name = models.CharField(max_length=255, default='', blank=True)
    signer_mother_name = models.CharField(max_length=255, null=True, blank=True)
    signer_birthdate = models.DateField(null=False, blank=False)  
    signer_cpf = models.CharField(max_length=14, unique=True) 
    signer_id = models.CharField(max_length=14, unique=True) 
    signer_rg_number = models.CharField(max_length=10)
    signer_rg_issuing_authority = models.CharField(max_length=10)
    signer_email = models.EmailField()
    signer_email_is_checked = models.BooleanField(default=False)
    signer_mobile_number = models.CharField(max_length=20, default="+55 (37) 9 NNNN-NNNN")
    signer_mobile_is_checked = models.BooleanField(default=False)
    signer_social_network_ID = models.JSONField(default=dict, choices=SOCIAL_ID_CHOICES)
    signer_signature_is_hidden = models.BooleanField(default=False)
    signing_datetime = models.DateTimeField(default=now)
    originating_ip = models.CharField(max_length=39)
    password = models.CharField(max_length=255)
    pdf_file = models.FileField(upload_to='pdfs/', blank=True, null=True)
    hash_and_time = models.CharField(max_length=255)
    pin_code = models.CharField(max_length=9)
    email_otp = models.CharField(max_length=6, blank=True, null=True)
    mobile_otp = models.CharField(max_length=6, blank=True, null=True)
    otp_created_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = 'Signer'
        verbose_name_plural = 'Signers'

    def __str__(self):
        return f"{self.signer_full_name} (CPF: {self.signer_cpf})"

    def clean(self):
        from django.core.exceptions import ValidationError
        import re
        if self.signer_cpf and not re.match(r'^\d{3}\.\d{3}\.\d{3}-\d{2}$|^\d{11}$', self.signer_cpf):
            raise ValidationError('Invalid CPF format. Use XXX.XXX.XXX-XX or 11 digits.')
        
        if self.signer_birthdate and self.signer_birthdate > datetime.date.today():
            raise ValidationError('Birthdate cannot be in the future.')