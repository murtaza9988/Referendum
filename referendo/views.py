from django.shortcuts import render, redirect
from django.contrib import messages
from django.core.mail import send_mail
from django.conf import settings
from django.utils import timezone
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import random
import hashlib
import datetime
from twilio.rest import Client

# Cryptography imports for digital signing
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives import serialization

from .forms import SignerForm, SignerOTPForm
from .models import Signer

# --------------------------
# Helper Functions
# --------------------------

def generate_otp():
    return str(random.randint(100000, 999999))

def send_sms_otp(phone_number, otp):
    try:
        account_sid = settings.TWILIO_ACCOUNT_SID
        auth_token = settings.TWILIO_AUTH_TOKEN
        from_number = settings.TWILIO_PHONE_NUMBER
        client = Client(account_sid, auth_token)
        client.messages.create(
            body=f"Your OTP verification code is: {otp}. Valid for 10 minutes.",
            from_=from_number,
            to=phone_number
        )
        return True
    except Exception as e:
        print(f"SMS sending error: {e}")
        return False

def check_voter_dv(voter_id):
    voter_id = ''.join([char for char in voter_id if char.isdigit()])
    if len(voter_id) < 12:
        return False
    sequential = voter_id[:8]
    uf = voter_id[8:10]
    vd1 = 0
    vd2 = 0
    summation = 0
    factor = 9
    for digit in sequential[::-1]:
        summation += int(digit) * factor
        factor -= 1
    remainder = summation % 11 
    if remainder == 10:
       vd1 = 0
    elif remainder == 0 and (uf == "01" or uf == "02"):
       vd1 = 1
    else:
       vd1 = remainder
    summation = 0
    factor = 7
    for digit in (uf + str(vd1)):
        summation += int(digit) * factor
        factor += 1
    remainder = summation % 11
    if remainder == 10:
       vd2 = 0
    elif remainder == 0 and (uf == "01" or uf == "02"):
       vd2 = 1
    else:
       vd2 = remainder
    return True if voter_id[-2:] == f"{vd1}{vd2}" else False

def check_cpf(cpf):
    cpf = ''.join([char for char in cpf if char.isdigit()])
    def dgt(cpf):
       vd = 0
       for m, d in enumerate(cpf[::-1]):
           vd += (m + 2) * int(d)
       vd = 11 - vd % 11
       if vd >= 10:
          vd = 0
       return cpf + str(vd)
    recalculated = dgt(dgt(cpf[:9]))
    return True if cpf == recalculated else False

def hash_and_sign_data(signer):
    try:
        with open("static/referendum_private_key.pem", "rb") as f:
            private_key = serialization.load_pem_private_key(f.read(), password=None)
    except Exception as e:
        print(f"Error loading private key: {e}")
        return None, None
    str_to_hash = (f"{signer.signer_full_name}"
                   f"{signer.gender}"
                   f"{signer.signer_birthdate}"
                   f"{signer.signer_cpf}"
                   f"{signer.signer_id}"
                   f"{signer.signer_email}"
                   f"{signer.signer_mobile_number}"
                   f"{signer.signing_datetime}"
                   f"{signer.originating_ip}")
    hashed_string = hashlib.sha256(str_to_hash.encode()).hexdigest()
    try:
        signature = private_key.sign(
            hashed_string.encode(),
            padding.PSS(
                mgf=padding.MGF1(hashes.SHA256()),
                salt_length=padding.PSS.MAX_LENGTH
            ),
            hashes.SHA256()
        )
    except Exception as e:
        print(f"Error signing data: {e}")
        signature = None
    return hashed_string, signature

# --------------------------
# View Endpoints
# --------------------------

@csrf_exempt
def send_otp(request):
    if request.method == 'POST':
        form_data = request.POST.dict()
        email = form_data.get('signer_email')
        phone_number = form_data.get('signer_mobile_number')
        if not email or not phone_number:
            return JsonResponse({"success": False, "message": "Email and mobile number are required."}, status=400)
        request.session['form_data'] = form_data
        email_otp = generate_otp()
        mobile_otp = generate_otp()
        print(f"Generated OTPs -- Email: {email_otp}, Mobile: {mobile_otp}")
        request.session['email_otp'] = email_otp
        request.session['mobile_otp'] = mobile_otp
        request.session['otp_created_at'] = timezone.now().isoformat()
        subject = 'Your Email Verification PIN Code'
        message_text = f'Your PIN code is: {email_otp}\nThis code is valid for 10 minutes.'
        from_email = settings.DEFAULT_FROM_EMAIL
        recipient_list = [email]
        email_sent = False
        try:
            send_mail(subject, message_text, from_email, recipient_list)
            email_sent = True
        except Exception as e:
            print(f"Email sending error: {e}")
        sms_sent = send_sms_otp(phone_number, mobile_otp)
        if email_sent and sms_sent:
            user_message = 'PIN codes sent to your email and mobile number.'
        elif email_sent:
            user_message = 'PIN sent to email but failed to send to mobile.'
        elif sms_sent:
            user_message = 'PIN sent to mobile but failed to send to email.'
        else:
            user_message = 'Failed to send PIN codes. Please try again.'
        return JsonResponse({"success": True, "message": user_message})
    else:
        return JsonResponse({"success": False, "message": "Invalid request method."}, status=405)

@csrf_exempt
def verify_signer(request):
    if request.method == 'POST':
        entered_email_pin = request.POST.get('email_pin')
        entered_mobile_pin = request.POST.get('mobile_pin')
        stored_email_pin = request.session.get('email_otp')
        stored_mobile_pin = request.session.get('mobile_otp')
        form_data = request.session.get('form_data')
        if not (entered_email_pin and entered_mobile_pin and stored_email_pin and stored_mobile_pin and form_data):
            print("DEBUG: Missing OTP or form data")
            return JsonResponse({"success": False, "message": "Missing OTP or form data. Please request new PIN codes."}, status=400)
        otp_created_at = timezone.datetime.fromisoformat(request.session.get('otp_created_at', ''))
        if (timezone.now() - otp_created_at).total_seconds() > 600:
            print("DEBUG: OTP expired")
            return JsonResponse({"success": False, "message": "PIN codes have expired. Please request new ones."}, status=400)
        if entered_email_pin == stored_email_pin and entered_mobile_pin == stored_mobile_pin:
            form = SignerOTPForm(form_data)
            if form.is_valid():
                print("DEBUG: Form is valid.")
                signer = form.save(commit=False)
                signer.signer_email_is_checked = True
                signer.signer_mobile_is_checked = True
                signer.email_otp = stored_email_pin
                signer.mobile_otp = stored_mobile_pin
                signer.otp_created_at = otp_created_at
                x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
                if x_forwarded_for:
                    signer.originating_ip = x_forwarded_for.split(',')[0]
                else:
                    signer.originating_ip = request.META.get('REMOTE_ADDR')
                hashed_string, signature = hash_and_sign_data(signer)
                signer.signer_hash = hashed_string
                signer.signer_signature = signature
                signer.save()
                for key in ['form_data', 'email_otp', 'mobile_otp', 'otp_created_at']:
                    if key in request.session:
                        del request.session[key]
                return JsonResponse({"success": True, "message": "Verification successful! Your signature has been submitted."})
            else:
                print("DEBUG: Form errors:", form.errors)
                return JsonResponse({"success": False, "message": "Form has errors. Please correct them.", "errors": form.errors}, status=400)
        else:
            if entered_email_pin != stored_email_pin and entered_mobile_pin != stored_mobile_pin:
                print("DEBUG: Both OTP codes invalid")
                return JsonResponse({"success": False, "message": "Both PIN codes are invalid. Please try again."}, status=400)
            elif entered_email_pin != stored_email_pin:
                print("DEBUG: Email OTP invalid")
                return JsonResponse({"success": False, "message": "Email PIN code is invalid. Please try again."}, status=400)
            elif entered_mobile_pin != stored_mobile_pin:
                print("DEBUG: Mobile OTP invalid")
                return JsonResponse({"success": False, "message": "Mobile PIN code is invalid. Please try again."}, status=400)
    else:
        return JsonResponse({"success": False, "message": "Invalid request method."}, status=405)

@csrf_exempt
def check_cpf_view(request):
    cpf = request.GET.get('cpf') or request.POST.get('cpf')
    if not cpf:
        return JsonResponse({"valid": False, "message": "No CPF provided."}, status=400)
    is_valid = check_cpf(cpf)
    if is_valid:
        return JsonResponse({"valid": True, "message": "CPF is valid."})
    else:
        return JsonResponse({"valid": False, "message": "Invalid CPF format. Use XXX.XXX.XXX-XX or 11 digits."}, status=400)

@csrf_exempt
def check_voter_id_view(request):
    voter_id = request.GET.get('voter_id') or request.POST.get('voter_id')
    if not voter_id:
        return JsonResponse({"valid": False, "message": "No Voter ID provided."}, status=400)
    is_valid = check_voter_dv(voter_id)
    if is_valid:
        return JsonResponse({"valid": True, "message": "Voter ID is valid."})
    else:
        return JsonResponse({"valid": False, "message": "Invalid Voter ID."}, status=400)

def signer_form(request):
    form = SignerForm()
    return render(request, 'signer_form.html', {'form': form})
