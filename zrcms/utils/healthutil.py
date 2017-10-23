import json

from django.http import HttpResponse


def health_check(request):
    response_data = dict()
    response_data['message'] = 'CMS is online and operational.'
    response_data['status'] = 0
    return HttpResponse(json.dumps(response_data), content_type="application/json")
