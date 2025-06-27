from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.views.generic import DetailView, UpdateView
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.urls import reverse_lazy
from django.contrib.auth import get_user_model
from .forms import CustomUserChangeForm

User = get_user_model()

@login_required
def profile(request):
    """
    View for displaying and updating the user's profile.
    """
    if request.method == 'POST':
        form = CustomUserChangeForm(
            request.POST, 
            instance=request.user,
            request=request  # Pass request to the form for email verification
        )
        if form.is_valid():
            try:
                user = form.save(commit=False)
                user.save()
                
                # Update session with new email if it was changed
                from django.contrib.auth import update_session_auth_hash
                update_session_auth_hash(request, user)
                
                # If email was changed, the form will have added its own message
                if 'email' not in form.changed_data:
                    messages.success(request, 'Your profile has been updated successfully!')
                
                return redirect('profile')
                
            except Exception as e:
                messages.error(
                    request, 
                    f'An error occurred while updating your profile: {str(e)}. Please try again.'
                )
        else:
            messages.error(
                request, 
                'Please correct the errors below.'
            )
    else:
        form = CustomUserChangeForm(
            instance=request.user,
            initial={
                'email': request.user.email,
                'first_name': request.user.first_name,
                'last_name': request.user.last_name,
            },
            request=request
        )
    
    # Get the primary email address for display
    email_address = None
    if hasattr(request.user, 'emailaddress_set'):
        try:
            email_address = request.user.emailaddress_set.get(primary=True)
        except:
            pass
    
    context = {
        'form': form,
        'email_address': email_address,
    }
    
    return render(request, 'users/profile.html', context)

class UserProfileView(LoginRequiredMixin, DetailView):
    model = User
    template_name = 'users/profile_detail.html'
    context_object_name = 'user_profile'
    slug_field = 'username'
    slug_url_kwarg = 'username'

class UserProfileUpdateView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    model = User
    form_class = CustomUserChangeForm
    template_name = 'users/profile_form.html'
    
    def get_success_url(self):
        return reverse_lazy('profile', kwargs={'username': self.request.user.username})
    
    def test_func(self):
        user = self.get_object()
        return self.request.user == user
