from django.contrib.auth import get_user_model
from django.test import TestCase, Client

from ..models import Group, Post

User = get_user_model()


class PostsURLTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.group = Group.objects.create(
            title='Тестовый заголовок',
            description='Тестовое описание',
            slug='test-slug'
        )
        cls.user = User.objects.create_user(username='test')
        cls.user_1 = User.objects.create_user(username='test1')
        cls.post = Post.objects.create(
            text='ъ' * 100,
            author=cls.user,
            group=cls.group
        )

    def setUp(self):
        self.guest_client = Client()
        self.authorised_client = Client()
        self.authorised_client.force_login(PostsURLTests.user)
        self.authorised_client_1 = Client()
        self.authorised_client_1.force_login(PostsURLTests.user_1)

    def test_urls_200_unauthorised(self):
        """Проверяет доступность страниц."""
        urls = [
            '/',
            f'/group/{self.group.slug}/',
            f'/{self.user.username}/',
            f'/{self.user.username}/{self.post.id}/'
        ]
        for adress in urls:
            with self.subTest(adress=adress):
                response = self.guest_client.get(adress)
                self.assertEqual(response.status_code, 200)

    def test_urls_redirect_unauthorised(self):
        """Проверяет перенаправление для неавторизованных пользователей. """
        url_redirects = {
            '/new/': '/auth/login/?next=/new/',
            f'/{self.user.username}/{self.post.id}/edit/':
            f'/auth/login/?next=/{self.user.username}/{self.post.id}/edit/',
            f'/{self.user.username}/{self.post.id}/comment':
            (f'/auth/login/?next=/{self.user.username}/'
             f'{self.post.id}/comment')
        }
        for adress, redirect in url_redirects.items():
            self.assertRedirects(self.guest_client.get(adress), redirect)

    def test_urls_redirect_authorised(self):
        """Проверяет перенаправление для авторизованных пользователей со
        страницы редактирования чужого поста."""
        response = self.authorised_client_1.get(
            f'/{self.user.username}/{self.post.id}/edit/'
        )
        self.assertRedirects(
            response,
            f'/{self.user.username}/{self.post.id}/'
        )

    def test_urls_200_authorised(self):
        """Проверяет доступность страниц для авторизованных пользователей."""
        adresses = [
            '/new/',
            f'/{self.user.username}/{self.post.id}/edit/'
        ]
        for adress in adresses:
            with self.subTest(adress=adress):
                self.assertEqual(
                    self.authorised_client.get(adress).status_code,
                    200
                )

    def test_urls_uses_correct_template(self):
        """URL-адрес использует соответствующий шаблон."""
        templates_url_names = {
            '/': 'posts/index.html',
            '/new/': 'posts/new_post.html',
            f'/group/{self.group.slug}/': 'posts/group.html',
            f'/{self.user.username}/{self.post.id}/': 'posts/post.html',
            f'/{self.user.username}/': 'posts/profile.html',
            f'/{self.user.username}/{self.post.id}/edit/':
            'posts/new_post.html',
            '/page404error/': 'misc/error.html'
        }
        for adress, template in templates_url_names.items():
            with self.subTest(adress=adress):
                response = self.authorised_client.get(adress)
                self.assertTemplateUsed(response, template)
