import shutil

from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse

from ..models import Post, Group

User = get_user_model()


class PostFormTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.group = Group.objects.create(
            description='Описание тестовой группы',
            title='Тестовое название',
            slug='test-group'
        )
        cls.group1 = Group.objects.create(
            description='Описание тестовой группы 1',
            title='Тестовое название 1',
            slug='test-group1'
        )
        cls.user = User.objects.create_user(username='test')
        cls.user1 = User.objects.create_user(username='test1')
        cls.post = Post.objects.create(
            text='ъ' * 100,
            author=cls.user,
            group=cls.group
        )

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(settings.MEDIA_ROOT, ignore_errors=True)
        super().tearDownClass()

    def setUp(self):
        cache.clear()
        self.authorised_client = Client()
        self.authorised_client.force_login(self.user)
        self.authorised_client1 = Client()
        self.authorised_client1.force_login(self.user1)
        self.unauthorised_client = Client()

    def test_edit_post(self):
        """Посты успешно изменяются после редактирования"""
        form = {
            'text': 'Новый текст',
            'group': self.group1.id
        }
        response = self.authorised_client.post(
            reverse(
                'post_edit',
                kwargs={
                    'username': self.user.username,
                    'id_post': self.post.id
                }
            ),
            form,
            follow=True
        )
        url_redirect = reverse(
            'post',
            kwargs={
                'username': self.user.username,
                'post_id': self.post.id
            }
        )
        self.post.refresh_from_db()
        self.assertRedirects(response, url_redirect)
        self.assertEqual(self.post.group, self.group1)
        self.assertEqual(self.post.text, form['text'])

    def test_create_post(self):
        """Валидная форма создает запись в Post."""
        small_gif = (
            b'\x47\x49\x46\x38\x39\x61\x02\x00'
            b'\x01\x00\x80\x00\x00\x00\x00\x00'
            b'\xFF\xFF\xFF\x21\xF9\x04\x00\x00'
            b'\x00\x00\x00\x2C\x00\x00\x00\x00'
            b'\x02\x00\x01\x00\x00\x02\x02\x0C'
            b'\x0A\x00\x3B'
        )
        uploaded = SimpleUploadedFile(
            name='small.gif',
            content=small_gif,
            content_type='image/gif'
        )

        form_data = {
            'text': 'Тестовый текст',
            'group': self.group.id,
            'image': uploaded
        }

        posts_count = Post.objects.count()
        response = self.authorised_client.post(
            reverse('new_post'),
            form_data,
            follow=True
        )

        self.assertRedirects(response, reverse('posts'))
        self.assertEqual(Post.objects.count(), posts_count + 1)

        self.assertTrue(
            Post.objects.filter(
                text='Тестовый текст',
                group=self.group,
                image='posts/small.gif'
            ).exists()
        )

    def test_not_edit_post(self):
        """Посты успешно не изменяются после редактирования,
        если пользователь редактирует чужой пост."""
        self.post.refresh_from_db()
        old_text = self.post.text
        form_data = {
            'text': 'Новый текст 2',
            'group': self.group.id
        }
        self.authorised_client1.post(
            reverse(
                'post_edit',
                kwargs={
                    'username': self.user.username,
                    'id_post': self.post.id
                }
            ),
            form_data,
        )

        self.post.refresh_from_db()
        self.assertEqual(self.post.text, old_text)

    def test_unauth_post(self):
        """Проверяет невозможность создать пост без
        авторизации."""
        form_data = {
            'text': 'Тестовый текст',
            'group': self.group,
        }

        posts_count = Post.objects.count()
        self.unauthorised_client.post(
            reverse('new_post'),
            form_data,
            follow=True
        )
        self.assertEqual(Post.objects.count(), posts_count)
