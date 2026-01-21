from django import forms
from .models import Comment, Post, Category
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserChangeForm


class UserUpdateForm(UserChangeForm):
    password = None
    
    class Meta:
        model = User
        fields = ['username', 'first_name', 'last_name', 'email']
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-control'}),
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
        }
        labels = {
            'username': 'Имя пользователя',
            'first_name': 'Имя',
            'last_name': 'Фамилия',
            'email': 'Email',
        }


class CommentForm(forms.ModelForm):
    class Meta:
        model = Comment
        fields = ['text']
  

class PostForm(forms.ModelForm):
    
    class Meta:
        model = Post
        fields = ['title', 'text', 'pub_date', 'category', 'location', 'image']
        widgets = {
            'pub_date': forms.DateTimeInput(
                attrs={
                    'class': 'form-control',
                    'type': 'datetime-local',
                    'id': 'datetimepicker'
                },
                format='%Y-%m-%dT%H:%M'  
            ),
            'title': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Заголовок поста'
            }),
            'text': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 12,
                'placeholder': 'Текст поста...'
            })
        }
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Фильтруем категории - только опубликованные
        self.fields['category'].queryset = Category.objects.filter(
            is_published=True
        ).order_by('title')