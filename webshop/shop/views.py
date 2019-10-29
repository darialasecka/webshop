from django.shortcuts import render, get_object_or_404
from .models import Category, Product, Review
from .forms import ReviewForm
from cart.forms import CartAddProductForm
from django.contrib.auth.decorators import login_required
from django.db.models import Count


def product_list(request, category_slug=None):
	category = None
	categories = Category.objects.all()
	products = Product.objects.filter(available=True)
	if category_slug:
		category = get_object_or_404(Category, slug=category_slug)
		products = products.filter(category=category)
	return render(request, 'shop/product/list.html', {'category': category, 'categories': categories, 'products': products})


@login_required
def add_review(request, new_review, product):
	review_form = ReviewForm(data=request.POST)
	if review_form.is_valid:
		new_review = review_form.save(commit=False)
		new_review.product = product
		new_review.user = request.user
		new_review.save()
	return new_review, review_form


def reviews_by_user_count(request, product):
	return Review.objects.filter(user=request.user, product=product).count()


@login_required
def delete_review(request):
	instance = Review.objects.filter(user=request.user)
	instance.delete()


def product_detail(request, id, slug):
	product = get_object_or_404(Product, id=id, slug=slug, available=True)
	cart_product_form = CartAddProductForm()
	reviews = product.review.filter(active=True)
	new_review = None
	users_reviews = None
	if request.user.is_authenticated:
		users_reviews = reviews_by_user_count(request, product)
	if request.method == 'POST' and users_reviews < 1:
		new_review, review_form = add_review(request, new_review, product)
	else:
		review_form = ReviewForm()
	return render(request, 'shop/product/detail.html', {'product': product, 
														'cart_product_form': cart_product_form, 
														'reviews' : reviews, 
														'new_review' : new_review,
														'review_form' : review_form,
														'users_reviews' : users_reviews })