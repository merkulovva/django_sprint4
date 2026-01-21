from django.shortcuts import render, get_list_or_404, get_object_or_404, redirect
from .models import Post, Category, Comment
from django.db.models import Count
from django.utils import timezone
from django.views.generic import ListView, DetailView, DeleteView, UpdateView, CreateView
from django.contrib.auth.models import User
from django.urls import reverse_lazy
from django.core.exceptions import PermissionDenied
from django.contrib.auth.decorators import login_required
from .forms import CommentForm, UserUpdateForm, PostForm
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import Http404


class PostListView(ListView):
    model = Post
    ordering = "id"
    paginate_by = 10
    template_name = 'blog/index.html'

    def get_queryset(self):
        queryset = Post.objects.select_related(
            'author', 'category', 'location'
        ).filter(
            is_published=True,
            category__is_published=True,

            pub_date__lte=timezone.now()).annotate(
            comment_count=Count('comment')
        ).order_by('-pub_date')

        return queryset


class ProfileListView(ListView):
    model = Post
    template_name = "blog/profile.html"
    context_object_name = 'page_obj'
    paginate_by = 10

    def get_queryset(self):
        username = self.kwargs['username']
        self.profile_user = get_object_or_404(User, username=username)
        
        # Базовый queryset: все посты пользователя
        queryset = Post.objects.filter(author=self.profile_user)
        
        # Если пользователь смотрит НЕ свой профиль
        if self.request.user != self.profile_user:
            # Показываем только опубликованные посты с опубликованными категориями
            queryset = queryset.filter(
                is_published=True,
                pub_date__lte=timezone.now(),
                category__is_published=True
            )
        # Если пользователь смотрит СВОЙ профиль
        # (оставляем все посты, включая черновики)
        
        # Аннотируем количество комментариев
        queryset = queryset.annotate(comment_count=Count('comment'))
        
        # Оптимизируем запросы
        queryset = queryset.select_related(
            'author', 'category', 'location'
        )
        
        return queryset.order_by('-pub_date')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['profile'] = self.profile_user

        return context


class PostDetailView(DetailView):
    model = Post
    template_name = 'blog/detail.html'

    def get_object(self, queryset=None):
        # Получаем объект обычным способом
        obj = super().get_object(queryset)
        
        # Проверяем права доступа
        if (not obj.is_published) or (not obj.category.is_published) or (obj.pub_date > timezone.now()):
            # Если пост не опубликован
            if not self.request.user.is_authenticated:
                # Неавторизованный пользователь - 404
                raise Http404("Пост не найден")
            elif self.request.user != obj.author:
                # Чужой неопубликованный пост - 404
                raise Http404("Пост не найден")
            # Если дошли сюда - пользователь авторизован и автор поста
            # Показываем пост
        return obj

    def get_list_of_comment(self):
        id = self.kwargs['pk']
        self.post_commented = get_object_or_404(Post, id=id)
        queryset = Comment.objects.filter(post=self.post_commented)
        print(queryset)
        return queryset.order_by('-created_at')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['form'] = CommentForm()
        context['comments'] = self.object.comment.all().order_by('created_at')
        return context


@login_required
def delete_comment(request, post_id, comment_id):
    comment = get_object_or_404(
        Comment.objects.select_related('author', 'post'),
        pk=comment_id,
        post_id=post_id
    )

    if request.user != comment.author:
        raise PermissionDenied("Вы не можете удалить этот комментарий")

    if request.method == 'GET':
        return render(request, 'blog/comment.html', {
            'comment': comment,
            'post_id': post_id,
        })

    elif request.method == 'POST':
        post_pk = comment.post.pk
        comment.delete()

        return redirect('blog:post_detail', pk=post_pk)


@login_required
def edit_post(request, post_id):
    post = get_object_or_404(
        Post.objects.select_related('author', 'location', 'category'), pk=post_id)

    if request.user != post.author:
        return redirect('blog:post_detail', post_id)

    if request.method == "GET":
        form = PostForm(instance=post)
        return render(request, 'blog/create.html', {
            'form': form, })
    elif request.method == "POST":
        form = PostForm(request.POST, instance=post)
        if form.is_valid():
            updated_post = form.save(commit=False)
            updated_post.save()
            return redirect('blog:post_detail', post_id)


@login_required
def delete_post(request, post_id):
    post = get_object_or_404(
        Post.objects.select_related('author', 'location', 'category'),
        pk=post_id
    )

    if request.user != post.author:
        raise PermissionDenied("Вы не можете удалить этот пост")

    if request.method == 'GET':
        form = PostForm(instance=post)
        return render(request, 'blog/create.html', {
            'post': post,
            'form': form
        })

    elif request.method == 'POST':
        post.delete()

        return redirect('blog:index')


@login_required
def edit_comment(request, post_id, comment_id):
    comment = get_object_or_404(
        Comment.objects.select_related('author', 'post'),
        pk=comment_id,
        post_id=post_id
    )

    if request.user != comment.author:
        raise PermissionDenied("Вы не можете редактировать чужой комментарий")

    if request.method == 'GET':
        form = CommentForm(instance=comment)
        return render(request, 'blog/comment.html', {
            'form': form,
            'comment': comment,
            'post': comment.post,
            'post_id': post_id,
        })

    elif request.method == 'POST':
        form = CommentForm(request.POST, instance=comment)

        if form.is_valid():
            updated_comment = form.save(commit=False)
            updated_comment.save()

            return redirect('blog:post_detail', pk=post_id)
        else:
            return render(request, 'blog/comment.html', {
                'form': form,
                'comment': comment,
                'post': comment.post,
                'post_id': post_id,
            })


@login_required
def add_comment(request, post_id):
    # Получаем объект дня рождения или выбрасываем 404 ошибку.
    post = get_object_or_404(Post, pk=post_id)
    # Функция должна обрабатывать только POST-запросы.
    form = CommentForm(request.POST)
    if form.is_valid():
        # Создаём объект поздравления, но не сохраняем его в БД.
        comment = form.save(commit=False)
        # В поле author передаём объект автора поздравления.
        comment.author = request.user
        # В поле birthday передаём объект дня рождения.
        comment.post = post
        # Сохраняем объект в БД.
        comment.save()
    # Перенаправляем пользователя назад, на страницу дня рождения.
    return redirect('blog:post_detail', pk=post_id)


class ProfileUpdateView(LoginRequiredMixin, UpdateView):
    model = User
    form_class = UserUpdateForm
    template_name = 'blog/user.html'
    success_url = reverse_lazy('blog:edit_profile')  # или другая страница

    def get_object(self, queryset=None):
        # Возвращаем текущего пользователя
        return self.request.user

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Добавляем username в контекст для шаблона
        context['username'] = self.request.user.username
        return context


class PostCreateView(LoginRequiredMixin, CreateView):
    model = Post
    template_name = 'blog/create.html'
    form_class = PostForm
    success_url = reverse_lazy('blog:')

    def form_valid(self, form):
        form.instance.author = self.request.user
        return super().form_valid(form)

    def get_success_url(self):
        return reverse_lazy(
            'blog:profile',
            kwargs={'username': self.request.user.username})


class CategoryListView(ListView):
    model = Category
    template_name = 'blog/category.html'
    context_object_name = 'page_obj'
    paginate_by = 10

    def get_queryset(self):
        category = self.kwargs['category_slug']
        self.category = get_object_or_404(
            Category, slug=category, is_published=True)
        queryset = Post.objects.select_related(
            "author",
            "location",
            "category").filter(
            is_published=True,
            category__slug=category,
            pub_date__lte=timezone.now(),
            category__is_published=True)

        return queryset.order_by('-pub_date')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        category = Category.objects.get(slug=self.kwargs['category_slug'])
        context['category'] = category
        return context
