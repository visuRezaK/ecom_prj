from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout


from userauths import forms as userauths_forms
from vendor import models as vendor_models
from userauths import models as userauths_models

def register_view(request):
    if request.user.is_authenticated:
        messages.warning(request, "You are already logged in")
        return redirect("/")
    
    form = userauths_forms.UserRegisterForm(request.POST or None)

    if form.is_valid():
        user = form.save()

        full_name = form.cleaned_data.get("full_name")
        email = form.cleaned_data.get("email")
        mobile = form.cleaned_data.get("mobile")
        password = form.cleaned_data.get("password1")
        user_type = form.cleaned_data.get("user_type")

        user = authenticate(email=email, password=password)
        if user is not None:
            login(request, user)

            messages.success(request, "Account was created successfully")
            profile = userauths_models.Profile.objects.create(full_name=full_name, mobile=mobile, user=user)

            if user_type == "Vendor":
                vendor_models.Vendor.objects.create(user=user, store_name=full_name)
                profile.user_Type = "Vendor"
            else:
                profile.user_Type = "Customer"

            profile.save()

            next_url = request.GET.get("next", "store:index")
            return redirect(next_url)
        else:
            messages.error(request, "Authentication failed")

    context = {
        "form": form
    }        

    return render(request, "userauths/sign-up.html", context)


def login_view(request):
    if request.user.is_authenticated:
        messages.warning(request, "You are already logged in")
        return redirect("/")

    if request.method == "POST":
        form = userauths_forms.LoginForm(request.POST or None)

        if form.is_valid():
            email = form.cleaned_data['email']
            password = form.cleaned_data['password']
            captcha_verified = form.cleaned_data.get('captcha', False)

            if captcha_verified:
                try:
                    user_instance = userauths_models.User.objects.get(email=email, is_active=True)
                    user_authenticate = authenticate(request, email=email, password=password)

                    if user_authenticate is not None:
                        login(request, user_authenticate)
                        messages.success(request, "You are logged in")
                        next_url = request.GET.get("next", "store:index")
                        return redirect(next_url)
                    else:
                        messages.error(request, "Username or password doesn't exist")    
                except userauths_models.User.DoesNotExist:
                    messages.error(request, 'User does not exist')     
            else:
                messages.error(request, "Captcha verification failed please try again")          

    else:
        form = userauths_forms.LoginForm()                  

    context = {
        "form": form
    }        

    return render(request, "userauths/sign-in.html", context)    

def logout_view(request):
    if 'cart_id' in request.session:
        cart_id = request.session['cart_id']
    else:
        cart_id = None

    logout(request)

    request.session['cart_id'] = cart_id
    messages.success(request, "You have been logged out")
    return redirect("userauths:sign-in")