from cart.paypal_payment import *

from io import BytesIO

import weasyprint
from django.core.mail import EmailMessage
from django.shortcuts import render
from cart.models import Order, OrderComponent
from django.contrib.admin.views.decorators import staff_member_required
from django.shortcuts import render, get_object_or_404, redirect
from django.template.loader import render_to_string
from webshop import settings
from .forms import OrderButtons, FilterButton, AddDeliverySearchingCode
from django.http import HttpResponseRedirect, HttpResponse
from django.utils import timezone
from customer.models import Complainment


def are_components_completed(components):
	if components != None:
		for component in components:
			if component.is_completed == False:
				return False
	return True


@staff_member_required
def manage_orders(request):
	orders = Order.objects.all()
	for order in orders:
		if (order.is_confirmed == False and order.expiration_date < timezone.now()) or order.are_products == False:
			order.delete()
	orders = Order.objects.all()
	if request.method == 'POST':
		form = OrderButtons(request.POST)
		if form.is_valid():
			val = form.cleaned_data.get("btn")
			if val == 'Opłacone zamówienia':
				orders = Order.objects.filter(is_confirmed=True)
			elif val == 'Skompletowane zamówienia':
				all_orders = Order.objects.filter()
				orders = []
				for order in all_orders:
					if order.are_products:
						components = OrderComponent.objects.filter(order=order)
						if are_components_completed(components):
							orders.append(order)
			elif val == 'Wszystkie zamówienia':
				orders = Order.objects.all()
			elif val == 'Wysłane zamówienia':
				orders = Order.objects.filter(is_sent=True)
			elif val == 'Lista produktów do skompletowania':
				return show_products(request)
			elif val == 'Opłacone zamówienia do skompletowania':
				conf_orders = Order.objects.filter(is_confirmed=True)
				orders = []
				for order in conf_orders:
					if order.are_products:
						components = OrderComponent.objects.filter(order=order)
						if are_components_completed(components) == False:
							orders.append(order)
	else:
		form = OrderButtons()
	return render(request, 'staff/manage_orders.html', {'orders': orders})


@staff_member_required
def show_order(request, id):
	order = get_object_or_404(Order, id=id)
	if request.method == 'POST':
		form = AddDeliverySearchingCode(request.POST)
		if form.is_valid():
			order.is_sent = True
			order.delivery_searching_code = form.cleaned_data.get('delivery_searching_code')
			order.save()
	else:
		form = AddDeliverySearchingCode()
	components = OrderComponent.objects.filter(order=order)
	return render(request, 'staff/show_order.html', {'order': order, 'components': components, 'form': form })


@staff_member_required
def refund_order(request, id):
	order = get_object_or_404(Order, id=id)
	message = 'Pieniądze za to zamówienie zostały juz zwrócone!'
	if not order.is_refunded:
		payment_id = order.payment_id
		try:
			make_refund(payment_id)
			order.is_refunded = True
			order.save()
			message = 'Pomyślnie dokonano zwrotu kwoty %.2fzł za zamówienie numer %06d' % (order.price, order.id)
		except:
			message = 'Nie udało się zwrócić pieniędzy za to zamówienie'
	return HttpResponse(message)



@staff_member_required
def show_products(request):
	components = OrderComponent.objects.all()
	return render(request, 'staff/component_list.html', {'components': components})


@staff_member_required
def completed_component(request, id):
	component = get_object_or_404(OrderComponent, id=id)
	component.is_completed = True
	component.save()
	return HttpResponseRedirect(request.META.get('HTTP_REFERER'))


@staff_member_required
def find_order(request):
	form = None
	orders = None
	if request.method == 'POST':
		form = FilterButton(request.POST)
		if form.is_valid():
			order_id = form.cleaned_data.get("order_id")
			orders = Order.objects.filter(id=order_id)
	else:
		form = FilterButton()
	return render(request, 'staff/finder.html', {'form': form, 'orders': orders})


@staff_member_required
def read_complainments(request):
	complainments = Complainment.objects.all()
	return render(request, 'staff/complainments.html', {'complainments': complainments})


@staff_member_required
def close_complainment(request, id):
	complainment = get_object_or_404(Complainment, id=id)
	complainment.is_active = False
	complainment.save()
	return redirect('staff:complainments')


@staff_member_required
def admin_order_pdf(request, order_id):
	order = get_object_or_404(Order, id=order_id)
	order_details = OrderComponent.objects.filter(order=order)
	html = render_to_string('staff/pdf.html', {'order': order, 'order_details': order_details})
	response = HttpResponse(content_type='application/pdf')
	response['Content-Disposition'] = 'filename="order_{}.pdf"'.format(order.id)
	weasyprint.HTML(string=html).write_pdf(response)
	return response


def send_pdf(order):
	# create invoice e-mail
	subject = 'Webshop - Zamówienie nr {}'.format(order.id)
	message = 'Faktura ostatniego zamówienia znajduje się w załączniku.'
	email = EmailMessage(subject, message, to=[order.user.email])
	# generate PDF
	order_details = OrderComponent.objects.filter(order=order)
	print(order_details)
	html = render_to_string('staff/pdf.html', {'order': order, 'order_details': order_details})
	out = BytesIO()
	weasyprint.HTML(string=html).write_pdf(out)
	# attach PDF file
	email.attach('order_{}.pdf'.format(order.id), out.getvalue(), 'application/pdf')
	# send e-mail
	email.send()
