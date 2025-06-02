from django.urls import path
from django.contrib.auth import views as auth_views
from .views import (
    blog_list, create_blog, update_blog, delete_blog, blog_detail, 
    home, article_detail, signup, signout, contact_us, article_list,
    article_search, about, create_checkout_session, payment_success,
    payment_cancel, stripe_webhook , predict_news
)

urlpatterns = [
    path('', home, name='home'),
    path('predict/', predict_news, name='predict'),

    path('article/<int:post_id>/', article_detail, name='article_detail'),
    path('signin/', auth_views.LoginView.as_view(template_name='signin.html'), name='signin'),
    path('signup/', signup, name='signup'),
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
]
