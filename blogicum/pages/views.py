from django.shortcuts import render


# Create your views here.
def about(request):
    template = "pages/about.html"
    return render(request, template)


def rules(request):
    template = "pages/rules.html"
    return render(request, template)

def page_not_found(request, exception):
    # Переменная exception содержит отладочную информацию; 
    # выводить её в шаблон пользовательской страницы 404 мы не станем.
    return render(request, 'pages/404.html', status=404) 


def csrf_failure(request, reason=''):
    return render(request, 'pages/403csrf.html', status=403) 


def server_failure(request, reason=''):
    return render(request, 'pages/500.html', status=500)