from django import forms
from django.contrib import messages
from django.contrib.auth.forms import UserCreationForm, UserChangeForm
from django.contrib.auth import get_user_model
from allauth.account.forms import SignupForm as AllauthSignupForm
from allauth.socialaccount.forms import SignupForm as SocialSignupForm

User = get_user_model()

class CustomUserCreationForm(UserCreationForm):
    class Meta:
        model = User
        fields = ('email', 'username')


class CustomUserChangeForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ('first_name', 'last_name', 'email')
    
    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request', None)
        super().__init__(*args, **kwargs)
        
        # Add Bootstrap classes to form fields
        for field in self.fields:
            self.fields[field].widget.attrs.update({'class': 'form-control'})
    
    def clean_email(self):
        email = self.cleaned_data.get('email')
        current_email = self.instance.email
        
        # If email hasn't changed, no need to check
        if email == current_email:
            return email
            
        # Check if email is already in use
        if User.objects.filter(email=email).exclude(pk=self.instance.pk).exists():
            raise forms.ValidationError('This email is already in use by another account.')
            
        return email
    
    def save(self, commit=True):
        user = super().save(commit=False)
        
        # If email was changed, update the email address in allauth
        if 'email' in self.changed_data:
            from allauth.account.models import EmailAddress
            
            # Update the primary email address
            try:
                email_address = EmailAddress.objects.get_primary(user)
                if email_address.email != user.email:
                    # Unset old primary
                    EmailAddress.objects.filter(user=user, primary=True).update(primary=False)
                    
                    # Create or update new email address
                    new_email, created = EmailAddress.objects.get_or_create(
                        user=user,
                        email=user.email,
                        defaults={'primary': True, 'verified': False}
                    )
                    if not created:
                        new_email.primary = True
                        new_email.verified = False
                        new_email.save()
                    
                    # Send verification email
                    from allauth.account.utils import send_email_confirmation
                    send_email_confirmation(self.request, user, email=user.email)
                    
                    messages.info(
                        self.request, 
                        'A verification email has been sent to your new email address. ' \
                        'Please verify it to complete the email change.'
                    )
            except Exception as e:
                # Log the error but don't fail the save
                import logging
                logger = logging.getLogger(__name__)
                logger.error(f"Error updating email address: {str(e)}")
        
        if commit:
            user.save()
        
        return user


class CustomAllauthSignupForm(AllauthSignupForm):
    first_name = forms.CharField(max_length=30, label='First Name', required=False)
    last_name = forms.CharField(max_length=30, label='Last Name', required=False)
    
    def save(self, request):
        user = super().save(request)
        user.first_name = self.cleaned_data['first_name']
        user.last_name = self.cleaned_data['last_name']
        user.save()
        return user


class CustomSocialSignupForm(SocialSignupForm):
    first_name = forms.CharField(max_length=30, label='First Name', required=False)
    last_name = forms.CharField(max_length=30, label='Last Name', required=False)
    
    def save(self, request):
        user = super().save(request)
        user.first_name = self.cleaned_data['first_name']
        user.last_name = self.cleaned_data['last_name']
        user.save()
        return user