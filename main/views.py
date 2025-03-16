from django.shortcuts import render, redirect
from django.contrib import messages
from .forms import SignerForm
from .models import Signer
from django.core.mail import send_mail
from django.conf import settings
import random
from django.utils import timezone
from django.http import JsonResponse
from twilio.rest import Client
from django.views.decorators.csrf import csrf_exempt

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

@csrf_exempt
def send_otp(request):
    """
    Receives all form data (from steps 1 & 2), generates OTPs, saves both the data and OTPs
    in the session, sends the OTPs via email and SMS, and returns a JSON response.
    """
    if request.method == 'POST':
        # Use request.POST dict (even if some fields are disabled, we send their values manually from JS)
        form_data = request.POST.dict()
        email = form_data.get('signer_email')
        phone_number = form_data.get('signer_mobile_number')
        
        if not email or not phone_number:
            return JsonResponse({"success": False, "message": "Email and mobile number are required."}, status=400)
        
        # Save the complete form data in session for later verification
        request.session['form_data'] = form_data
        
        # Generate OTPs
        email_otp = generate_otp()
        mobile_otp = generate_otp()
        print(f"Generated OTPs -- Email: {email_otp}, Mobile: {mobile_otp}")
        
        # Save OTPs and timestamp in session
        request.session['email_otp'] = email_otp
        request.session['mobile_otp'] = mobile_otp
        request.session['otp_created_at'] = timezone.now().isoformat()
        
        # Send Email OTP
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
        
        # Send SMS OTP via Twilio
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
    """
    Verifies the OTP codes submitted by the user. If valid (and within 10 minutes),
    rebuilds the form using the stored session data, saves the record to the database,
    clears the session, and returns a JSON response.
    """
    if request.method == 'POST':
        entered_email_pin = request.POST.get('email_pin')
        entered_mobile_pin = request.POST.get('mobile_pin')
        stored_email_pin = request.session.get('email_otp')
        stored_mobile_pin = request.session.get('mobile_otp')
        form_data = request.session.get('form_data')
        
        if not (entered_email_pin and entered_mobile_pin and stored_email_pin and stored_mobile_pin and form_data):
            return JsonResponse({"success": False, "message": "Missing OTP or form data. Please request new PIN codes."}, status=400)
        
        otp_created_at = timezone.datetime.fromisoformat(request.session.get('otp_created_at', ''))
        
        # Check for expiration (10 minutes)
        if (timezone.now() - otp_created_at).total_seconds() > 600:
            return JsonResponse({"success": False, "message": "PIN codes have expired. Please request new ones."}, status=400)
        
        if entered_email_pin == stored_email_pin and entered_mobile_pin == stored_mobile_pin:
            form = SignerForm(form_data)
            if form.is_valid():
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
                
                signer.save()
                
                # Clear session data
                for key in ['form_data', 'email_otp', 'mobile_otp', 'otp_created_at']:
                    if key in request.session:
                        del request.session[key]
                
                return JsonResponse({"success": True, "message": "Verification successful! Your signature has been submitted."})
            else:
                return JsonResponse({"success": False, "message": "Form has errors. Please correct them."}, status=400)
        else:
            if entered_email_pin != stored_email_pin and entered_mobile_pin != stored_mobile_pin:
                return JsonResponse({"success": False, "message": "Both PIN codes are invalid. Please try again."}, status=400)
            elif entered_email_pin != stored_email_pin:
                return JsonResponse({"success": False, "message": "Email PIN code is invalid. Please try again."}, status=400)
            elif entered_mobile_pin != stored_mobile_pin:
                return JsonResponse({"success": False, "message": "Mobile PIN code is invalid. Please try again."}, status=400)
    else:
        return JsonResponse({"success": False, "message": "Invalid request method."}, status=405)

def signer_form(request):
    """
    Renders the multi-step form. The OTP sending and verification are handled via separate AJAX endpoints.
    """
    form = SignerForm()
    return render(request, 'signer_form.html', {'form': form})
