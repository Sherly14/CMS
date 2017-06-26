# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import render
from django.views import View


# Create your views here.


class SampleView(View, LoginRequiredMixin):

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

