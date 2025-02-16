from django.contrib import admin
from userauths import models
from .models import User, Profile



admin.site.register(User)
admin.site.register(Profile)

