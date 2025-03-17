from django.urls import path
from referendo import views

urlpatterns = [
    path('', views.signer_form, name='signer_form'),
    path('api/send-otp/', views.send_otp, name='send_otp'),
    path('api/verify/', views.verify_signer, name='verify_signer'),
    path('api/check-cpf/', views.check_cpf_view, name='check_cpf'),
    path('api/check-voter-id/', views.check_voter_id_view, name='check_voter_id'),
]
