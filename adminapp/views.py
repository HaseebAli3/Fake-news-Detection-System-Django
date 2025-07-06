from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.forms import AuthenticationForm
from django.http import HttpResponse, JsonResponse
from django.core.paginator import Paginator
from django.contrib.auth.decorators import login_required
from django.conf import settings
from django.db.models import Q
from django.contrib import messages
from django.core.mail import send_mail
from django.utils import timezone
import json
import stripe
from django.views.decorators.csrf import csrf_exempt
import random
import string
import logging
import uuid  # Added to fix NameError
from .models import BlogPost, Comment, OTP, Profile
from .ml_model import predict_fake_news
from .forms import CustomUserCreationForm
from django.contrib.auth.models import User

# Set up logging for debugging
logger = logging.getLogger(__name__)

def predict_news(request):
    results = []
    if request.method == "POST":
        news_text = request.POST.get('news_text')
        if news_text:
            results = predict_fake_news(news_text)
            print(results)
            if results == [{'error': 'No fact-checks found for this claim.'}]:
                results = None
    return render(request, "predict_form.html", {"results": results})

def donation_success(request):
    return render(request, 'success.html')

def donation_cancel(request):
    return render(request, 'donation_cancel.html', {
        'message': 'Your donation was not completed. Please try again later.'
    })

stripe.api_key = settings.STRIPE_SECRET_KEY

@csrf_exempt
def create_checkout_session(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            amount = data.get('amount')
            if not amount or not isinstance(amount, (int, float)) or amount <= 0:
                return JsonResponse({'error': 'Invalid amount'}, status=400)
            session = stripe.checkout.Session.create(
                payment_method_types=['card'],
                line_items=[{
                    'price_data': {
                        'currency': 'usd',
                        'product_data': {
                            'name': 'Donation',
                            'description': 'Support our mission to fight fake news',
                        },
                        'unit_amount': int(amount * 100),
                    },
                    'quantity': 1,
                }],
                mode='payment',
                success_url=request.build_absolute_uri('/payment/success/'),
                cancel_url=request.build_absolute_uri('/payment/cancel/'),
                metadata={
                    'user_id': request.user.id if request.user.is_authenticated else 'anonymous',
                    'donation_amount': amount,
                }
            )
            return JsonResponse({'sessionId': session.id})
        except stripe.error.StripeError as e:
            return JsonResponse({'error': str(e)}, status=400)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
    return JsonResponse({'error': 'Invalid request method'}, status=405)

@csrf_exempt
def stripe_webhook(request):
    payload = request.body
    sig_header = request.META.get('HTTP_STRIPE_SIGNATURE')
    endpoint_secret = settings.STRIPE_WEBHOOK_SECRET
    try:
        event = stripe.Webhook.construct_event(payload, sig_header, endpoint_secret)
    except (ValueError, stripe.error.SignatureVerificationError):
        return HttpResponse(status=400)
    if event['type'] == 'checkout.session.completed':
        session = event['data']['object']
        user_id = session.metadata.get('user_id')
        amount = float(session.metadata.get('donation_amount', 0))
    return HttpResponse(status=200)

def payment_success(request):
    return render(request, 'payment/success.html', {
        'message': 'Thank you for your donation! Your support helps us continue our mission.'
    })

def payment_cancel(request):
    return render(request, 'payment/cancel.html', {
        'message': 'Your donation was not completed. You can try again if you wish.'
    })

def article_list(request):
    query = request.GET.get('q', '')
    articles = BlogPost.objects.filter(
        Q(title__icontains=query) | Q(content__icontains=query)
    ).order_by('-created_at') if query else BlogPost.objects.all().order_by('-created_at')
    paginator = Paginator(articles, 9)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return render(request, 'art_list.html', {'articles': page_obj.object_list})
    return render(request, 'articles.html', {'page_obj': page_obj, 'query': query})

def article_search(request):
    query = request.GET.get('q', '')
    return redirect(f'/articles/?q={query}')

def home(request):
    posts = BlogPost.objects.all().order_by('-created_at')
    paginator = Paginator(posts, 6)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return render(request, 'article_list.html', {'page_obj': page_obj})
    return render(request, 'home.html')

def contact_us(request):
    return render(request, 'contactus.html')

def about(request):
    return render(request, 'aboutus.html')

def article_detail(request, post_id):
    post = get_object_or_404(BlogPost, id=post_id)
    comments = post.comments.all().order_by('-created_at')
    if request.method == 'POST' and request.user.is_authenticated:
        content = request.POST.get('content')
        if content:
            Comment.objects.create(post=post, user=request.user, content=content)
            return redirect('article_detail', post_id=post_id)
    return render(request, 'article_detail.html', {'post': post, 'comments': comments})

def signin(request):
    if request.method == 'POST':
        email = request.POST.get('email', '').strip()
        password = request.POST.get('password', '')
        logger.debug(f"Signin attempt with email: {email}, password: {'*' * len(password) if password else 'None'}")
        if not email or not password:
            messages.error(request, "Email and password are required.")
            logger.warning("Signin failed: Missing email or password")
            return render(request, 'signin.html')
        try:
            user = User.objects.get(email__iexact=email)
            logger.debug(f"User found with email: {email}, username: {user.username}")
            user = authenticate(request, username=user.username, password=password)
            if user is not None:
                login(request, user)
                #logger.info(f"User {user.username} logged in successfully")
               # messages.success(request, "Login successful.")
                return redirect('home')
            else:
                messages.error(request, "Invalid email or password.")
                logger.warning(f"Signin failed for email: {email} - Invalid credentials")
        except User.DoesNotExist:
            messages.error(request, "No user found with this email address.")
            logger.warning(f"Signin failed: No user found with email {email}")
        except Exception as e:
            messages.error(request, "An error occurred during login. Please try again.")
            logger.error(f"Signin error for email {email}: {str(e)}")
        return render(request, 'signin.html')
    logger.debug("Rendering signin page for GET request")
    return render(request, 'signin.html')

def signup(request):
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data.get('email')
            logger.debug(f"Signup attempt with email: {email}, display_name: {form.cleaned_data.get('display_name')}")
            request.session['signup_form_data'] = {
                'display_name': form.cleaned_data.get('display_name'),
                'email': email,
                'password1': form.cleaned_data.get('password1'),
                'password2': form.cleaned_data.get('password2'),
            }
            otp = ''.join(random.choices(string.digits, k=6))
            expires_at = timezone.now() + timezone.timedelta(minutes=10)
            OTP.objects.create(email=email, otp_code=otp, expires_at=expires_at)
            try:
                subject = 'Signup Verification OTP'
                message = f'Your OTP for signup verification is: {otp}. It is valid for 10 minutes.'
                send_mail(subject, message, settings.EMAIL_HOST_USER, [email], fail_silently=False)
                messages.success(request, 'An OTP has been sent to your email.')
                logger.info(f"OTP sent for email: {email}")
                return redirect('signup_verify_otp', email=email)
            except Exception as e:
                messages.error(request, 'Failed to send OTP. Please try again.')
                logger.error(f"Signup OTP error for email {email}: {str(e)}")
        else:
            logger.warning(f"Signup form invalid: {form.errors}")
        return render(request, 'signup.html', {'form': form})
    else:
        form = CustomUserCreationForm()
    return render(request, 'signup.html', {'form': form})

def signup_verify_otp(request, email):
    if request.method == 'POST':
        otp = request.POST.get('otp', '').strip()
        logger.debug(f"OTP verification attempt for email: {email}, OTP: {otp}")
        try:
            otp_obj = OTP.objects.filter(email__iexact=email, otp_code=otp).latest('created_at')
            if otp_obj.expires_at < timezone.now():
                otp_obj.delete()
                messages.error(request, 'OTP has expired. Please try signing up again.')
                request.session.pop('signup_form_data', None)
                logger.warning(f"OTP expired for email: {email}")
                return redirect('signup')
            form_data = request.session.get('signup_form_data')
            if not form_data:
                messages.error(request, 'Session expired. Please try signing up again.')
                logger.warning(f"Session expired for email: {email}")
                return redirect('signup')
            user = User.objects.create_user(
                username=form_data['display_name'], 
                email=form_data['email'],
                password=form_data['password1']
            )
            Profile.objects.create(user=user, display_name=form_data['display_name'])
            user.save()
            otp_obj.delete()
            login(request, user)
            messages.success(request, 'Register successfully.')
            logger.info(f"User {user.username} created and logged in successfully")
            request.session.pop('signup_form_data', None)
            return redirect('articles')  # Updated to match URL name in urls.py
        except OTP.DoesNotExist:
            messages.error(request, 'Invalid OTP.')
            logger.warning(f"Invalid OTP for email: {email}")
        except Exception as e:
            messages.error(request, 'An error occurred during OTP verification. Please try again.')
            logger.error(f"OTP verification error for email {email}: {str(e)}")
        return render(request, 'signup_verify_otp.html', {'email': email})
    return render(request, 'signup_verify_otp.html', {'email': email})

def signout(request):
    logout(request)
    current_url = request.META.get('HTTP_REFERER', '/')
    return redirect(current_url)

def blog_detail(request, blog_id):
    blog = get_object_or_404(BlogPost, id=blog_id)
    return render(request, 'blog_detail.html', {'blog': blog})

def blog_list(request):
    query = request.GET.get('search')
    blogs = BlogPost.objects.filter(title__icontains=query) if query else BlogPost.objects.all().order_by('-created_at')
    return render(request, 'blog_list.html', {'blogs': blogs})

def create_blog(request):
    if request.method == "POST":
        title = request.POST['title']
        content = request.POST['content']
        thumbnail = request.FILES.get('thumbnail')
        BlogPost.objects.create(title=title, content=content, thumbnail=thumbnail)
        return redirect('blog_list')
    return render(request, 'create_blog.html')

def update_blog(request, blog_id):
    blog = get_object_or_404(BlogPost, id=blog_id)
    if request.method == "POST":
        blog.title = request.POST['title']
        blog.content = request.POST['content']
        if 'thumbnail' in request.FILES:
            blog.thumbnail = request.FILES['thumbnail']
        blog.save()
        return redirect('blog_list')
    return render(request, 'update_blog.html', {'blog': blog})

def delete_blog(request, blog_id):
    blog = get_object_or_404(BlogPost, id=blog_id)
    blog.delete()
    return redirect('blog_list')

def resend_otp(request, email):
    if request.method == 'GET':
        otp = ''.join(random.choices(string.digits, k=6))
        expires_at = timezone.now() + timezone.timedelta(minutes=10)
        OTP.objects.filter(email__iexact=email).delete()
        OTP.objects.create(email=email, otp_code=otp, expires_at=expires_at)
        try:
            subject = 'Signup Verification OTP'
            message = f'Your new OTP for signup verification is: {otp}. It is valid for 10 minutes.'
            send_mail(subject, message, settings.EMAIL_HOST_USER, [email], fail_silently=False)
            messages.success(request, 'A new OTP has been sent to your email.')
            logger.info(f"Resend OTP sent for email: {email}")
        except Exception as e:
            messages.error(request, 'Failed to send OTP. Please try again.')
            logger.error(f"Resend OTP error for email {email}: {str(e)}")
        return redirect('signup_verify_otp', email=email)
    else:
        messages.error(request, 'Invalid request method.')
        return redirect('signup')

def password_reset_request(request):
    if request.method == 'POST':
        email = request.POST.get('email')
        try:
            user = User.objects.get(email__iexact=email)
            otp = ''.join(random.choices(string.digits, k=6))
            expires_at = timezone.now() + timezone.timedelta(minutes=10)
            OTP.objects.create(user=user, otp_code=otp, expires_at=expires_at)
            subject = 'Password Reset OTP'
            message = f'Your OTP for password reset is: {otp}. It is valid for 10 minutes.'
            send_mail(subject, message, settings.EMAIL_HOST_USER, [email], fail_silently=False)
            messages.success(request, 'An OTP has been sent to your email.')
            return redirect('password_reset_verify', email=email)
        except User.DoesNotExist:
            messages.error(request, 'No user found with this email address.')
            logger.warning(f"Password reset failed: No user found with email {email}")
    return render(request, 'password_reset_request.html')

def password_reset_verify(request, email):
    if request.method == 'POST':
        otp = request.POST.get('otp')
        password = request.POST.get('password')
        try:
            user = User.objects.get(email__iexact=email)
            otp_obj = OTP.objects.filter(user=user, otp_code=otp).latest('created_at')
            if otp_obj.expires_at < timezone.now():
                messages.error(request, 'OTP has expired. Please request a new one.')
                return redirect('password_reset_request')
            user.set_password(password)
            user.save()
            otp_obj.delete()
            messages.success(request, 'Password has been reset successfully.')
            return redirect('signin')
        except (User.DoesNotExist, OTP.DoesNotExist):
            messages.error(request, 'Invalid OTP or user.')
            logger.warning(f"Password reset OTP verification failed for email: {email}")
    return render(request, 'password_reset_verify.html', {'email': email})