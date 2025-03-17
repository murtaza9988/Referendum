from django.urls import path
from referendo import views

urlpatterns = [
    path('', views.signer_form, name='signer_form'),
    path('api/send-otp/', views.send_otp, name='send_otp'),
    path('api/verify/', views.verify_signer, name='verify_signer'),
]
