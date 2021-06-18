from django.shortcuts import render, get_object_or_404
from django.core.paginator import Paginator
from django.contrib.auth import get_user_model
from django.urls import reverse_lazy, reverse
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseRedirect
from django.views.generic import CreateView
from django.contrib.auth.mixins import LoginRequiredMixin

from .forms import PostForm, CommentForm
from .models import Post, Group, Follow
from yatube import settings

User = get_user_model()


def profile(request, username):
    """Выводит последние посты автора по PAGE_MAX на страницу."""
    author = get_object_or_404(User, username=username)
    posts = author.posts.all()
    posts_amount = posts.count()
    user = author.follower.count()
    following = author.following.count()
    paginator = Paginator(posts, settings.PAGE_MAX)
    page_number = request.GET.get('page')
    page = paginator.get_page(page_number)
    if request.user.is_authenticated:
        is_followed = Follow.objects.filter(
            author__username=username,
            user=request.user
        ).exists()
    else:
        is_followed = False
    return render(
        request, 'posts/profile.html', {'page': page,
                                        'posts_amount': posts_amount,
                                        'author': author,
                                        'follower': user,
                                        'following': following,
                                        'is_followed': is_followed}
    )


def post_view(request, username, post_id):
    """Выводит один конкретный пост."""
    post = get_object_or_404(
        Post,
        id=post_id,
        author__username=username
    )
    author = post.author
    posts_amount = author.posts.count()
    user = author.follower.count()
    following = author.following.count()
    if request.user.is_authenticated:
        is_followed = Follow.objects.filter(
            author__username=username,
            user=request.user
        ).exists()
    else:
        is_followed = False
    context = {
        'post': post,
        'author': post.author,
        'comments': post.comments.all(),
        'posts_amount': posts_amount,
        'follower': user,
        'following': following,
        'is_followed': is_followed,
    }
    if request.user.is_authenticated:
        form = CommentForm(request.POST or None)
        context = {
            'post': post,
            'author': post.author,
            'comments': post.comments.all(),
            'posts_amount': posts_amount,
            'follower': user,
            'following': following,
            'is_followed': is_followed,
            'form': form
        }
        if form.is_valid():
            form.instance.author = request.user
            form.instance.post = post
            form.save()
            return HttpResponseRedirect(reverse(
                'post',
                args=[username, post_id])
            )
    return render(
        request,
        'posts/post.html',
        context
    )


def index(request):
    """Выводит последние посты по дате, по PAGE_MAX на странице."""
    posts_all = Post.objects.select_related('author').all()
    paginator = Paginator(posts_all, settings.PAGE_MAX)
    page_number = request.GET.get('page')
    page = paginator.get_page(page_number)
    return render(request,
                  'posts/index.html',
                  {'page': page, }
                  )


def group_posts(request, slug):
    """Выводит последние посты по PAGE_MAX на странице,
    только посты из группы."""
    group = get_object_or_404(Group, slug=slug)
    posts_all = group.posts.select_related('author').all()
    paginator = Paginator(posts_all, settings.PAGE_MAX)
    page_number = request.GET.get('page')
    page = paginator.get_page(page_number)
    return render(request,
                  'posts/group.html',
                  {'page': page,
                   'group': group}
                  )


class NewPosts(LoginRequiredMixin, CreateView):
    """View - класс для создания пользователями новых постов, позволяет
     выбрать группу для публикации."""
    form_class = PostForm
    success_url = reverse_lazy('posts')
    template_name = 'posts/new_post.html'
    login_url = reverse_lazy('login')

    def form_valid(self, form):
        form.instance.author = self.request.user
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['edit_check'] = 0
        return context


@login_required
def post_edit(request, username, id_post):
    """View - функция для редактирования пользователями их
    постов."""
    post_redacted = get_object_or_404(
        Post,
        id=id_post,
        author__username=username
    )
    url_redirect = reverse(
        'post',
        kwargs={
            'username': username,
            'post_id': id_post
        }
    )
    if not post_redacted.author == request.user:
        return HttpResponseRedirect(url_redirect)

    form = PostForm(
        request.POST or None,
        files=request.FILES or None,
        instance=post_redacted
    )

    if form.is_valid():
        form.save()
        return HttpResponseRedirect(url_redirect)
    else:
        return render(
            request,
            'posts/new_post.html',
            {'form': form, 'edit_check': 1, 'post': post_edit}
        )


@login_required
def add_comment(request, username, post_id):
    """Позволяет создавать комментарии."""
    post = get_object_or_404(
        Post,
        id=post_id
    )
    form = CommentForm(request.POST or None)
    if form.is_valid():
        form.instance.author = request.user
        form.instance.post = post
        form.save()
        return HttpResponseRedirect(reverse('post', args=[username, post_id]))

    author = post.author
    posts_amount = author.posts.count()
    user = author.follower.count()
    following = author.following.count()
    is_followed = Follow.objects.filter(
        author__username=username,
        user=request.user
    ).exists()
    return render(
        request,
        'posts/post.html', {
            'post': post,
            'author': post.author,
            'comments': post.comments.all(),
            'posts_amount': posts_amount,
            'follower': user,
            'following': following,
            'is_followed': is_followed,
            'form': form,
        }
    )


@login_required
def follow_index(request):
    """Показывает посты от избранных авторов."""
    subscriptions = request.user.follower.values_list('author__id', flat=True)
    posts_all = Post.objects.filter(author__id__in=subscriptions)
    paginator = Paginator(posts_all, settings.PAGE_MAX)
    page_number = request.GET.get('page')
    page = paginator.get_page(page_number)
    return render(request,
                  'posts/follow.html',
                  {'page': page, }
                  )


@login_required
def profile_follow(request, username):
    """Подписывает на профиль."""
    if username == request.user.username:
        return HttpResponseRedirect(request.META.get('HTTP_REFERER'))
    if Follow.objects.filter(
        author__username=username,
        user=request.user
    ).exists() is False:
        author = User.objects.get(username=username)
        Follow.objects.create(author=author, user=request.user)
    return HttpResponseRedirect(request.META.get('HTTP_REFERER'))


@login_required
def profile_unfollow(request, username):
    """Отписывает от профиля."""
    record = Follow.objects.filter(
        author__username=username,
        user=request.user
    )
    if record.exists:
        record.delete()
    return HttpResponseRedirect(request.META.get('HTTP_REFERER'))


def page_not_found(request, exception):
    return render(
        request,
        'misc/error.html',
        {'path': request.path, 'error': 404},
        status=404
    )


def server_error(request):
    return render(request, "misc/error.html", {'error': 500}, status=500)
