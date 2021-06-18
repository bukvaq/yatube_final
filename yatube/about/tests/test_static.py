from django.urls import reverse
from django.test import Client, TestCase


class StaticURLTests(TestCase):
    def setUp(self):
        self.guest_client = Client()

    def test_about_url_exists_at_desired_location(self):
        """Проверка доступности адресов приложения."""
        adresses = [
            '/about/tech/',
            '/about/author/'
        ]
        for i in adresses:
            with self.subTest(adress=i):
                response = self.guest_client.get(i)
                self.assertEqual(response.status_code, 200)

    def test_about_url_uses_correct_template(self):
        """Проверка шаблона для адресов приложения."""
        cases = {
            'about:tech': 'about/tech.html',
            'about:author': 'about/author.html'
        }
        for adress, template in cases.items():
            with self.subTest(adress=adress):
                response = self.guest_client.get(reverse(adress))
                self.assertTemplateUsed(response, template)
