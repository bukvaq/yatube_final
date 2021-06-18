from django.views.generic.base import TemplateView


class about_author_view(TemplateView):
    """Выводит информацию об авторе."""
    template_name = 'about/author.html'


class about_tech_view(TemplateView):
    """Выводит инофрмацию о технологиях, применённых при создании сайта."""
    template_name = 'about/tech.html'
