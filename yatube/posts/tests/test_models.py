from django.test import TestCase
from django.contrib.auth import get_user_model

from ..models import Post, Group

User = get_user_model()


class ModelTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.group = Group.objects.create(
            description='Описание тестовой группы',
            title='Тестовое название',
            slug='test-group'
        )

        cls.user = User.objects.create_user(username='Пользователь')

        cls.post = Post.objects.create(
            text='ъ' * 150,
            author=cls.user,
            group=cls.group
        )

    def test_str_(self):
        """Тестирует метод __str__ моделей."""
        results = {
            ModelTest.post.__str__(): self.post.text[:15],
            ModelTest.group.__str__(): self.group.description
        }
        with self.subTest():
            for i in results:
                self.assertEqual(results[i], i)
