import shutil

from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.contrib.auth import get_user_model
from django.test import TestCase, Client
from django.urls import reverse
from django import forms

from ..models import Group, Post, Follow
from yatube import settings

User = get_user_model()


class PostsViewTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.group = Group.objects.create(
            title='Тестовый заголовок',
            description='Тестовое описание',
            slug='test-slug'
        )
        cls.group1 = Group.objects.create(
            title='Тестовый заголовок1',
            description='Тестовое описание1',
            slug='test-slug1'
        )
        cls.user = User.objects.create_user(username='test')
        cls.user1 = User.objects.create_user(username='test1')
        cls.follow = Follow.objects.create(
            author=cls.user,
            user=cls.user1
        )
        small_gif = (
            b'\x47\x49\x46\x38\x39\x61\x02\x00'
            b'\x01\x00\x80\x00\x00\x00\x00\x00'
            b'\xFF\xFF\xFF\x21\xF9\x04\x00\x00'
            b'\x00\x00\x00\x2C\x00\x00\x00\x00'
            b'\x02\x00\x01\x00\x00\x02\x02\x0C'
            b'\x0A\x00\x3B'
        )
        cls.uploaded = SimpleUploadedFile(
            name='small.gif',
            content=small_gif,
            content_type='image/gif'
        )
        cls.post = Post.objects.create(
            text='ъ' * 100,
            author=cls.user,
            group=cls.group,
            image=cls.uploaded
        )

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(settings.MEDIA_ROOT, ignore_errors=True)
        super().tearDownClass()

    def setUp(self):
        self.guest_client = Client()
        self.authorised_client = Client()
        self.authorised_client.force_login(self.user)
        self.authorised_client1 = Client()
        self.authorised_client1.force_login(self.user1)
        cache.clear()

    def test_pages_use_correct_template(self):
        """Тест того, что view - функция использует соответствующий шаблон."""
        templates_pages_names = {
            'posts/index.html': reverse('posts'),
            'posts/group.html': reverse('group', args=[self.group.slug]),
            'posts/new_post.html': reverse('new_post'),
            'posts/profile.html': reverse(
                'profile',
                args=[self.user.username]
            ),
        }

        for template, reverse_name in templates_pages_names.items():
            with self.subTest(reverse_name=reverse_name):
                response = self.authorised_client.get(reverse_name)
                self.assertTemplateUsed(response, template)

    def test_posts_context(self):
        """Шаблоны index, group, profile и post сформированы с
        правильным контекстом."""
        adress_context = [
            [reverse('posts'), 'page'],
            [reverse('group', args=[self.group.slug]), 'page'],
            [reverse('profile', args=[self.user.username]), 'page'],
            [reverse('post', args=[self.user.username, self.post.id]), 'post']
        ]

        for i in adress_context:
            with self.subTest(adress=i[0]):
                response = self.authorised_client.get(i[0])
                all_posts = response.context[i[1]]
                if hasattr(all_posts, '__iter__'):
                    first_post = all_posts[0]
                else:
                    first_post = all_posts

                self.assertEqual(first_post.author, self.user)
                self.assertEqual(first_post.text, 'ъ' * 100)
                self.assertEqual(first_post.pub_date, self.post.pub_date)
                self.assertEqual(first_post.group, self.group)
                self.assertEqual(self.post.image, 'posts/small.gif')

    def test_forms_post(self):
        """Шаблоны с формами сформированы с правильным контекстом."""
        adresses = [
            reverse('new_post'),
            reverse('post_edit', args=[self.user.username, self.post.id])
        ]
        for i in adresses:
            with self.subTest(adress=i):
                response = self.authorised_client.get(i)
                form_fields = {
                    'group': forms.fields.ChoiceField,
                    'text': forms.fields.CharField,
                    'image': forms.fields.ImageField,
                }
                for value, expected in form_fields.items():
                    with self.subTest(value=value):
                        form_field = response.context['form'].fields[value]
                        self.assertIsInstance(form_field, expected)

    def test_group_post(self):
        """Пост виден в нужной группе и не виден в ненужной."""
        response = self.authorised_client.get(
            reverse('group', args=[self.group.slug])
        )
        response1 = self.authorised_client.get(
            reverse('group', args=[self.group1.slug])
        )
        a = len(response.context['page'])
        b = len(response1.context['page'])
        self.assertNotEqual(a, 0)
        self.assertEqual(b, 0)

    def test_cache_index(self):
        """Тестирует кэширование записей на главной странице."""
        response1 = self.guest_client.get(reverse('posts'))
        response1 = self.guest_client.get(reverse('posts'))
        new_post = Post.objects.create(
            text='Новый пост',
            author=self.user
        )
        response2 = self.guest_client.get(reverse('posts'))
        self.assertEqual(
            response1.context.get('page')[0].text,
            response2.context.get('page')[0].text
        )
        cache.clear()
        response2 = self.guest_client.get(reverse('posts'))
        self.assertEqual(
            response1.context.get('page')[0].text,
            new_post.text
        )

    def test_auth_subscribe(self):
        """Тестирует возможность подписываться и отписываться от
        других пользователей."""
        self.authorised_client.get(
            reverse('profile_follow', args=[self.user1.username])
        )
        self.assertEqual(
            Follow.objects.filter(
                user=self.user,
                author=self.user1
            ).exists(),
            True
        )

        self.authorised_client.get(
            reverse('profile_unfollow', args=[self.user1.username])
        )
        self.assertEqual(
            Follow.objects.filter(
                user=self.user,
                author=self.user1
            ).exists(),
            False
        )

    def test_comment_unauth(self):
        """Тестирует возможность комментировать."""
        form = {
            'text': 'Текст',
        }
        self.guest_client.post(
            reverse('add_comment', args=[self.user.username, self.post.id]),
            form
        )
        self.assertEqual(self.post.comments.count(), 0)

        self.authorised_client.post(
            reverse('add_comment', args=[self.user.username, self.post.id]),
            form
        )
        self.assertEqual(self.post.comments.count(), 1)

    def test_sub(self):
        """Созданный автором пост не появляется в ленте
        подписок у тех, кто на него не подписан."""
        response = self.authorised_client.get(reverse('follow_index'))
        self.assertEqual(len(response.context.get('page')), 0)
        response = self.authorised_client1.get(reverse('follow_index'))
        self.assertEqual(
            response.context.get('page')[0].text,
            self.post.text
        )


class PaginatorViewsTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.user = User.objects.create_user(username='test')

        for i in range(1, settings.PAGE_MAX + 6):
            Post.objects.create(
                text='ъ' * 100,
                author=cls.user,
            )
        cls.client = Client()

    def test_paginator_max(self):
        """Тестирует максимальное количество записей на старницу,
        обращаясь к главной странице."""
        response = self.client.get(reverse('posts'))
        self.assertEqual(
            len(response.context.get('page')),
            settings.PAGE_MAX
        )

    def test_paginator_last_page(self):
        """Тестирует корректность вычичления отсатка
        записей на последней странице"""
        response = self.client.get(reverse('posts') + '?page=2')
        self.assertEqual(len(response.context.get('page')), 5)
