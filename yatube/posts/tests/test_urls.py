from http import HTTPStatus
from django.test import TestCase, Client
from django.urls import reverse

from ..models import Group, Post, User


AUTHOR_USERNAME = 'TestAuthor'
USER_USERNAME = 'TestUser'
GROUP_TITLE = 'Тестовая группа'
GROUP_SLUG = 'test-slug'
GROUP_DESCRIPTION = 'Тестовое описание'
POST_TEXT = 'Тестовый текст'

INDEX_URL = reverse('posts:index')
GROUP_LIST_URL = reverse('posts:group_list', args=[GROUP_SLUG])
PROFILE_URL = reverse('posts:profile', args=[AUTHOR_USERNAME])
POST_CREATE_URL = reverse('posts:post_create')
LOGIN_URL = reverse('users:login')
UNEXISTING_PAGE = '/unexisting_page/'
FOLLOW_URL = reverse('posts:follow_index')
PROFILE_FOLLOW_URL = reverse('posts:profile_follow', args=[AUTHOR_USERNAME])
PROFILE_UNFOLLOW_URL = reverse('posts:profile_unfollow',
                               args=[AUTHOR_USERNAME])


class PostsURLTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.author_user = User.objects.create_user(username=AUTHOR_USERNAME)
        Group.objects.create(
            title=GROUP_TITLE,
            slug=GROUP_SLUG,
            description=GROUP_DESCRIPTION,
        )
        cls.post = Post.objects.create(
            text=POST_TEXT,
            author=cls.author_user,
        )
        cls.POST_EDIT_URL = reverse('posts:post_edit', args=[cls.post.id])
        cls.POST_DETAIL_URL = reverse('posts:post_detail', args=[cls.post.id])
        cls.guest = Client()
        cls.user = User.objects.create_user(username=USER_USERNAME)
        cls.another = Client()
        cls.another.force_login(cls.user)
        cls.author = Client()
        cls.author.force_login(cls.author_user)

    def test_urls_status_codes(self):
        url_client_status_codes = [
            [INDEX_URL, self.guest, HTTPStatus.OK],
            [GROUP_LIST_URL, self.guest, HTTPStatus.OK],
            [PROFILE_URL, self.guest, HTTPStatus.OK],
            [POST_CREATE_URL, self.another, HTTPStatus.OK],
            [self.POST_EDIT_URL, self.author, HTTPStatus.OK],
            [self.POST_DETAIL_URL, self.guest, HTTPStatus.OK],
            [FOLLOW_URL, self.author, HTTPStatus.OK],
            [FOLLOW_URL, self.guest, HTTPStatus.FOUND],
            [PROFILE_FOLLOW_URL, self.author, HTTPStatus.FOUND],
            [PROFILE_FOLLOW_URL, self.another, HTTPStatus.FOUND],
            [PROFILE_FOLLOW_URL, self.guest, HTTPStatus.FOUND],
            [PROFILE_UNFOLLOW_URL, self.author, HTTPStatus.FOUND],
            [PROFILE_UNFOLLOW_URL, self.another, HTTPStatus.FOUND],
            [PROFILE_UNFOLLOW_URL, self.guest, HTTPStatus.FOUND],
            [UNEXISTING_PAGE, self.guest, HTTPStatus.NOT_FOUND],
            [POST_CREATE_URL, self.guest, HTTPStatus.FOUND],
            [self.POST_EDIT_URL, self.guest, HTTPStatus.FOUND],
            [self.POST_EDIT_URL, self.another, HTTPStatus.FOUND],
        ]
        for url, client, status_code in url_client_status_codes:
            with self.subTest(url=url, client=client):
                self.assertEqual(client.get(url).status_code, status_code)

    def test_redirections_access_rights(self):
        url_client_redirections = [
            [POST_CREATE_URL, self.guest,
             f'{LOGIN_URL}?next={POST_CREATE_URL}'],
            [self.POST_EDIT_URL, self.guest,
             f'{LOGIN_URL}?next={self.POST_EDIT_URL}'],
            [self.POST_EDIT_URL, self.another, self.POST_DETAIL_URL],
            [PROFILE_FOLLOW_URL, self.guest,
             f'{LOGIN_URL}?next={PROFILE_FOLLOW_URL}'],
            [PROFILE_FOLLOW_URL, self.author, PROFILE_URL],
            [PROFILE_FOLLOW_URL, self.another, PROFILE_URL],
            [PROFILE_UNFOLLOW_URL, self.guest,
             f'{LOGIN_URL}?next={PROFILE_UNFOLLOW_URL}'],
            [PROFILE_UNFOLLOW_URL, self.author, PROFILE_URL],
            [PROFILE_UNFOLLOW_URL, self.another, PROFILE_URL],
        ]
        for url, client, redirection in url_client_redirections:
            with self.subTest(url=url, client=client):
                self.assertRedirects(client.get(url, follow=True), redirection)

    def test_urls_use_correct_templates(self):
        urls_templates = {
            INDEX_URL: 'posts/index.html',
            GROUP_LIST_URL: 'posts/group_list.html',
            PROFILE_URL: 'posts/profile.html',
            POST_CREATE_URL: 'posts/create_post.html',
            self.POST_EDIT_URL: 'posts/create_post.html',
            self.POST_DETAIL_URL: 'posts/post_detail.html',
            FOLLOW_URL: 'posts/follow.html',
        }
        for url, template in urls_templates.items():
            with self.subTest(url=url):
                self.assertTemplateUsed(self.author.get(url), template)
