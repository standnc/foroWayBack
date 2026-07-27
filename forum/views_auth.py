from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import render
from django.views import View
from django.contrib.auth import login as auth_login
from allauth.account.forms import LoginForm, SignupForm
from allauth.account.adapter import get_adapter
import logging

logger = logging.getLogger("foro")

class InlineLoginView(View):
    template_name = "forum/_login_form.html"

    def post(self, request, *args, **kwargs):
        form = LoginForm(request=request, data=request.POST, files=request.FILES)
        if form.is_valid():
            try:
                resp = form.login(request)
                if resp:
                    response = HttpResponse()
                    response["HX-Redirect"] = "/"
                    return response
            except Exception as e:
                logger.exception("InlineLogin error")
                response = HttpResponse()
                response["HX-Redirect"] = "/"
                return response
        return render(request, self.template_name, {"form": form}, status=422)

    def get(self, request, *args, **kwargs):
        return HttpResponseRedirect("/")


class InlineSignupView(View):
    template_name = "forum/_signup_form.html"

    def post(self, request, *args, **kwargs):
        form = SignupForm(request=request, data=request.POST, files=request.FILES)
        if form.is_valid():
            try:
                user = form.save(request)
                from allauth.account.utils import perform_login
                from allauth.account.internal.flows.signup import complete_signup
                resp = complete_signup(request, user=user, redirect_url="/", by_passkey=False)
                if resp:
                    response = HttpResponse()
                    response["HX-Redirect"] = "/"
                    return response
            except Exception as e:
                logger.exception("InlineSignup error")
                response = HttpResponse()
                response["HX-Redirect"] = "/"
                return response
        return render(request, self.template_name, {"form": form}, status=422)

    def get(self, request, *args, **kwargs):
        return HttpResponseRedirect("/")
