from django.urls import path
from django.contrib.auth import views as auth_views
from .views import (
    blog_list, create_blog, update_blog, delete_blog, blog_detail, 
    home, article_detail, signup, signup_verify_otp, signout, contact_us, article_list,
    article_search, about, create_checkout_session, payment_success,
    payment_cancel, stripe_webhook, predict_news, password_reset_request,
    password_reset_verify, resend_otp, signin
)

urlpatterns = [
    path('', home, name='home'),
    path('predict/', predict_news, name='predict'),
    path('article/<int:post_id>/', article_detail, name='article_detail'),
    path('signin/', signin, name='signin'),
    path('signup/', signup, name='signup'),
    path('signup/verify/<str:email>/', signup_verify_otp, name='signup_verify_otp'),
    path('signout/', signout, name='signout'),
    path('contact/', contact_us, name='contactus'),
    path('about/', about, name='about'),
    path('donate/', create_checkout_session, name='donate'),
    path('payment/success/', payment_success, name='payment_success'),
    path('payment/cancel/', payment_cancel, name='payment_cancel'),
    path('webhook/', stripe_webhook, name='stripe_webhook'),
    path('blog_list/', blog_list, name='blog_list'),
    path('articles/', article_list, name='articles'),
    path('search/', article_search, name='article_search'),
    path('create/', create_blog, name='create_blog'),
    path('update/<int:blog_id>/', update_blog, name='update_blog'),
    path('delete/<int:blog_id>/', delete_blog, name='delete_blog'),
    path('blog/<int:blog_id>/', blog_detail, name='blog_detail'),
    path('password/reset/', password_reset_request, name='password_reset_request'),
    path('password/reset/verify/<str:email>/', password_reset_verify, name='password_reset_verify'),
    path('signup/resend-otp/<str:email>/', resend_otp, name='resend_otp'),
]