import datetime
from django import forms
from django.core.exceptions import ValidationError
from .models import Signer
import re

class SignerForm(forms.ModelForm):
    signer_birthdate = forms.DateField(
        widget=forms.DateInput(attrs={'type': 'date'})
    )
    password = forms.CharField(widget=forms.PasswordInput)
    signer_social_network_ID = forms.ChoiceField(
        choices=[
            ('google', 'Google'),
            ('facebook', 'Facebook'),
            ('twitter', 'Twitter') 
        ],
        widget=forms.Select()
    )
    signing_datetime = forms.DateTimeField(
        required=False,
        widget=forms.DateTimeInput(attrs={'type': 'datetime-local'})
    )

    class Meta:
        model = Signer
        exclude = ['email_otp', 'mobile_otp', 'otp_created_at', 'originating_ip', 
                   'signer_email_is_checked', 'signer_mobile_is_checked',
                   'hash_and_time', 'signing_datetime']
        widgets = {
            'signer_full_name': forms.TextInput(attrs={'placeholder': 'Enter your full name'}),
            'signer_cpf': forms.TextInput(attrs={'placeholder': 'XXX.XXX.XXX-XX'}),
            'signer_id': forms.TextInput(attrs={'placeholder': 'Enter your voter ID'}),
            'signer_email': forms.EmailInput(attrs={'placeholder': 'Enter your email'}),
            'signer_mobile_number': forms.TextInput(attrs={'placeholder': '+55 (XX) 9XXXX-XXXX'}),
            'signer_signature_is_hidden': forms.CheckboxInput(),
        }

    def clean_signer_cpf(self):
        cpf = self.cleaned_data['signer_cpf']
        if not re.match(r'^\d{3}\.\d{3}\.\d{3}-\d{2}$|^\d{11}$', cpf):
            raise ValidationError('Invalid CPF format. Use XXX.XXX.XXX-XX or 11 digits.')
        return cpf

    def clean_signer_email(self):
        email = self.cleaned_data['signer_email']
        if Signer.objects.filter(signer_email=email).exclude(pk=self.instance.pk).exists():
            raise ValidationError('This email is already registered.')
        return email

    def clean_signer_mobile_number(self):
        mobile = self.cleaned_data['signer_mobile_number']
        pattern = r'^\+?\d{0,2}\s?\(?\d{2,3}\)?\s?\d{4,5}[-.\s]?\d{4}$'
        if not re.match(pattern, mobile):
            raise ValidationError('Invalid mobile format. Use +XX (XX) 9XXXX-XXXX or similar formats.')
        return mobile

    def clean_signer_social_network_ID(self):
        social_id = self.cleaned_data['signer_social_network_ID']
        valid_choices = dict(self.fields['signer_social_network_ID'].choices).keys()  
        if social_id not in valid_choices:
            raise ValidationError("Invalid choice. Please select Google, Facebook, or Twitter.")
        return social_id

    def clean(self):
        cleaned_data = super().clean()
        birthdate = cleaned_data.get('signer_birthdate')
        if birthdate and birthdate > datetime.date.today():
            raise ValidationError('Birthdate cannot be in the future.')
        return cleaned_data

# New form for OTP verification that only includes the fields you collect in your multi-step UI.
class SignerOTPForm(forms.ModelForm):
    class Meta:
        model = Signer
        # Only include fields that are collected in your UI
        fields = ['signer_full_name', 'gender', 'signer_birthdate', 'signer_cpf',
                  'signer_id', 'signer_email', 'signer_mobile_number', 'signer_signature_is_hidden']
