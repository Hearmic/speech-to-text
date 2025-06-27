from django.shortcuts import render, redirect
from django.contrib import messages
from django.core.mail import send_mail
from django.conf import settings
from django.views.generic import FormView
from django.urls import reverse_lazy

from main.forms import ContactForm

class ContactView(FormView):
    template_name = 'main/contact.html'
    form_class = ContactForm
    success_url = reverse_lazy('contact_success')

    def get_initial(self):
        initial = super().get_initial()
        plan = self.request.GET.get('plan')
        if plan:
            initial['plan'] = plan
            initial['subject'] = f"Subscription Inquiry - {plan} Plan"
        return initial

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['plan'] = self.request.GET.get('plan')
        return context

    def form_valid(self, form):
        # Get form data
        name = form.cleaned_data['name']
        email = form.cleaned_data['email']
        plan = form.cleaned_data.get('plan', 'General Inquiry')
        message = form.cleaned_data['message']

        # Send email
        subject = f"Subscription Inquiry: {plan} Plan"
        email_message = f"""
        New subscription inquiry from {name} ({email}):
        
        Plan: {plan}
        
        Message:
        {message}
        """

        try:
            send_mail(
                subject=subject,
                message=email_message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[settings.CONTACT_EMAIL],
                fail_silently=False,
            )
            messages.success(self.request, 'Your message has been sent! We will get back to you soon.')
        except Exception as e:
            messages.error(self.request, 'There was an error sending your message. Please try again later.')
            return super().form_invalid(form)

        return super().form_valid(form)

def contact_success(request):
    return render(request, 'main/contact_success.html')
