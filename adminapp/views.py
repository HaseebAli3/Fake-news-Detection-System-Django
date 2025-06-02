from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth import login, authenticate ,logout
from django.contrib.auth.forms import UserCreationForm ,AuthenticationForm
from django.http import HttpResponse, JsonResponse
from .models import BlogPost, Comment
from django.core.paginator import Paginator
from django.contrib.auth.decorators import login_required
from django.conf import settings 
# Show all blogs

from django.shortcuts import render
from django.core.paginator import Paginator
from django.db.models import Q
import json

import stripe
from django.conf import settings
from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt


from .ml_model import predict_fake_news  # <- import the function

def predict_news(request):
    if request.method == "POST":
        news_text = request.POST.get('news_text')  # get the input text
        if news_text:
            prediction = predict_fake_news(news_text)
            return render(request, "predict_form.html", {"prediction": prediction})
    return render(request, "predict_form.html")


# Set up your Stripe secret key
def donation_success(request):
    return render(request, 'success.html')

# views.py
def donation_cancel(request):
    return render(request, 'donation_cancel.html', {
        'message': 'Your donation was not completed. Please try again later.'
    })

# Initialize Stripe with your secret key
stripe.api_key = 'sk_test_51RHj8OGhl0mNQDnbOWwsKZtiJFMrMkssSaiP3tWHP4h6OcpPlFEYuSDdHcC3JkZtAExPi9m6sMEkYklXt87u7pXy00pvFV6Edc'

@csrf_exempt
def create_checkout_session(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            amount = data.get('amount')
            
            if not amount or not isinstance(amount, (int, float)) or amount <= 0:
                return JsonResponse({'error': 'Invalid amount'}, status=400)

            # Create a Stripe Checkout Session
            session = stripe.checkout.Session.create(
                payment_method_types=['card'],
                line_items=[{
                    'price_data': {
                        'currency': 'usd',
                        'product_data': {
                            'name': 'Donation',
                            'description': 'Support our mission to fight fake news',
                        },
                        'unit_amount': int(amount * 100),  # Convert to cents
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
    sig_header = request.META['HTTP_STRIPE_SIGNATURE']
    endpoint_secret = settings.STRIPE_WEBHOOK_SECRET

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, endpoint_secret
        )
    except ValueError as e:
        return HttpResponse(status=400)
    except stripe.error.SignatureVerificationError as e:
        return HttpResponse(status=400)

    # Handle the event
    if event['type'] == 'checkout.session.completed':
        session = event['data']['object']
        
        # Get the donation details from the session metadata
        user_id = session.metadata.get('user_id')
        amount = float(session.metadata.get('donation_amount', 0))
        
        # Here you can save the donation details to your database
        # For example:
        # Donation.objects.create(
        #     user_id=user_id if user_id != 'anonymous' else None,
        #     amount=amount,
        #     stripe_session_id=session.id,
        #     status='completed'
        # )

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
    # Get search query if present
    query = request.GET.get('q', '')
    
    # Filter articles based on search query
    if query:
        articles = BlogPost.objects.filter(
            Q(title__icontains=query) | Q(content__icontains=query)
        ).order_by('-created_at')
    else:
        articles = BlogPost.objects.all().order_by('-created_at')

    # Pagination
    paginator = Paginator(articles, 9)  # Show 9 articles per page
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)

    # Check if the request is AJAX for "Load More"
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return render(request, 'art_list.html', {'articles': page_obj.object_list})

    return render(request, 'articles.html', {'page_obj': page_obj, 'query': query})

def article_search(request):
    # Redirect search to article_list with query parameter
    query = request.GET.get('q', '')
    return redirect(f'/articles/?q={query}')
def home(request):
    posts = BlogPost.objects.all().order_by('-created_at')  # Latest posts first
    paginator = Paginator(posts, 6)  # Show 6 posts per page
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        # Return HTML snippet for AJAX
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
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(username=username, password=password)
            if user is not None:
                login(request, user)
                return redirect('home')
            else:
                form.add_error(None, "Invalid username or password")
    else:
        form = AuthenticationForm()
    return render(request, 'signin.html', {'form': form})
from django.contrib.auth.models import User

def signup(request):
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            # Explicitly ensure regular user properties
            user.is_staff = False
            user.is_superuser = False
            user.save()
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password1')
            user = authenticate(username=username, password=password)
            login(request, user)
            return redirect('home')
    else:
        form = UserCreationForm()
    return render(request, 'signup.html', {'form': form})


def signout(request):
    logout(request)
    return redirect('home')
def blog_detail(request, blog_id):
    blog = get_object_or_404(BlogPost, id=blog_id)
    return render(request, 'blog_detail.html', {'blog': blog})

def blog_list(request):
    query = request.GET.get('search')
    if query:
        blogs = BlogPost.objects.filter(title__icontains=query)
    else:
        blogs = BlogPost.objects.all().order_by('-created_at')  # Latest first
    return render(request, 'blog_list.html', {'blogs': blogs})

# Create new blog
def create_blog(request):
    if request.method == "POST":
        title = request.POST['title']
        content = request.POST['content']
        thumbnail = request.FILES.get('thumbnail')

        BlogPost.objects.create(title=title, content=content, thumbnail=thumbnail)
        return redirect('blog_list')

    return render(request, 'create_blog.html')

# Update blog
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

# Delete blog
def delete_blog(request, blog_id):
    blog = get_object_or_404(BlogPost, id=blog_id)
    blog.delete()
    return redirect('blog_list')

