# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.contrib.auth import login
from django.shortcuts import render
from django.views import View

from zruser.forms import LoginForm


def login_view(request):
    form = LoginForm(request.POST or None)
    if request.POST and form.is_valid():
        user = form.login(request)
        if user:
            login(request, user)
            return render(request, 'user_profile.html')
    return render(request, 'login.html', {'login_form': form})


class SampleView(View):

    def get(self, request, pk, *args, **kwargs):
        if request.user.is_authenticated():
            context = {
                'hello': 1,
                'user': request.user.__dict__
            }
        else:
            context = {
                'hello': 11,
                'user': request.user.__dict__
            }

        print pk, args, kwargs, request

        return render(request, "users_profile.html", context)

