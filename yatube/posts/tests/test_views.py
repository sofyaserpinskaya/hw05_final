import shutil
import tempfile

from django.conf import settings
from django.core.cache import cache
from django.core.cache.utils import make_template_fragment_key
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from ..models import Follow, Group, Post, User
from ..settings import POSTS_PER_PAGE


AUTHOR_USERNAME = 'TestAuthor'
USER_USERNAME = 'TestUser'
GROUP_TITLE = 'Тестовая группа'
GROUP_SLUG = 'test-slug'
GROUP_DESCRIPTION = 'Тестовое описание'
POST_TEXT = 'Тестовый текст'
GROUP_2_TITLE = 'Тестовая группа2'
GROUP_2_SLUG = 'test-slug2'
GROUP_2_DESCRIPTION = 'Тестовое описание2'
SMALL_GIF = (
    b'\x47\x49\x46\x38\x39\x61\x02\x00'
    b'\x01\x00\x80\x00\x00\x00\x00\x00'
    b'\xFF\xFF\xFF\x21\xF9\x04\x00\x00'
    b'\x00\x00\x00\x2C\x00\x00\x00\x00'
    b'\x02\x00\x01\x00\x00\x02\x02\x0C'
    b'\x0A\x00\x3B'
)

INDEX_URL = reverse('posts:index')
GROUP_LIST_URL = reverse('posts:group_list', args=[GROUP_SLUG])
GROUP_LIST_2_URL = reverse('posts:group_list', args=[GROUP_2_SLUG])
PROFILE_URL = reverse('posts:profile', args=[AUTHOR_USERNAME])
POST_CREATE_URL = reverse('posts:post_create')
FOLLOW_URL = reverse('posts:follow_index')
PROFILE_FOLLOW_URL = reverse('posts:profile_follow', args=[AUTHOR_USERNAME])
PROFILE_UNFOLLOW_URL = reverse('posts:profile_unfollow',
                               args=[AUTHOR_USERNAME])

TEMP_MEDIA_ROOT = tempfile.mkdtemp(dir=settings.BASE_DIR)


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class PostPagesTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.uploaded = SimpleUploadedFile(
            name='small.gif',
            content=SMALL_GIF,
            content_type='image/gif'
        )
        cls.author_user = User.objects.create_user(username=AUTHOR_USERNAME)
        cls.group = Group.objects.create(
            title=GROUP_TITLE,
            slug=GROUP_SLUG,
            description=GROUP_DESCRIPTION,
        )
        cls.post = Post.objects.create(
            text=POST_TEXT,
            author=cls.author_user,
            group=cls.group,
            image=cls.uploaded,
        )
        cls.POST_EDIT_URL = reverse('posts:post_edit', args=[cls.post.id])
        cls.POST_DETAIL_URL = reverse('posts:post_detail', args=[cls.post.id])
        cls.group2 = Group.objects.create(
            title=GROUP_2_TITLE,
            slug=GROUP_2_SLUG,
            description=GROUP_2_DESCRIPTION,
        )
        cls.author = Client()
        cls.author.force_login(cls.author_user)
        cls.user = User.objects.create_user(username=USER_USERNAME)
        cls.another = Client()
        cls.another.force_login(cls.user)

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)

    def test_index_profile_group_list_post_detail_show_correct_context(self):
        urls = [INDEX_URL, GROUP_LIST_URL, PROFILE_URL, self.POST_DETAIL_URL]
        for url in urls:
            request = self.author.get(url)
            with self.subTest(url=url):
                if url != self.POST_DETAIL_URL:
                    page_obj = request.context['page_obj']
                    self.assertEqual(len(page_obj), 1)
                    post = page_obj[0]
                else:
                    post = request.context['post']
                self.assertEqual(post.text, self.post.text)
                self.assertEqual(post.author, self.post.author)
                self.assertEqual(post.group, self.post.group)
                self.assertEqual(post.id, self.post.id)
                self.assertEqual(post.image, self.post.image)

    def test_post_does_not_exist_on_wrong_group_list_page(self):
        response = self.author.get(GROUP_LIST_2_URL)
        self.assertNotIn(self.post, response.context['page_obj'])

    def test_author_on_profile_page(self):
        self.assertEqual(self.author.get(PROFILE_URL).context['author'],
                         self.author_user)

    def test_group_on_group_list_page(self):
        group = self.author.get(GROUP_LIST_URL).context['group']
        self.assertEqual(group.title, self.group.title)
        self.assertEqual(group.description, self.group.description)
        self.assertEqual(group.slug, self.group.slug)
        self.assertEqual(group.id, self.group.id)

    def test_follow_unfollow_authors(self):
        self.assertEqual(Follow.objects.count(), 0)
        response = self.another.post(PROFILE_FOLLOW_URL)
        self.assertEqual(Follow.objects.count(), 1)
        follow = Follow.objects.first()
        self.assertEqual(follow.user.username, self.user.username)
        self.assertEqual(follow.author.username, self.author_user.username)
        self.assertRedirects(response, PROFILE_URL)
        response = self.another.post(PROFILE_UNFOLLOW_URL)
        self.assertEqual(Follow.objects.count(), 0)
        self.assertRedirects(response, PROFILE_URL)

    def test_post_on_follow_page(self):
        response = self.another.post(PROFILE_FOLLOW_URL)
        response = self.another.get(FOLLOW_URL)
        self.assertIn(self.post, response.context['page_obj'])

    def test_post_does_not_exist_on_wrong_follow_page(self):
        response = self.another.get(FOLLOW_URL)
        self.assertNotIn(self.post, response.context['page_obj'])

    def test_cache_index_page(self):
        Post.objects.all().delete()
        self.assertIn(self.post.text.encode('utf-8'),
                      self.author.get(INDEX_URL).content)
        cache.delete(make_template_fragment_key('index_page'))
        self.assertNotIn(self.post.text.encode('utf-8'),
                         self.author.get(INDEX_URL).content)


class PaginatorViewsTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.author_user = User.objects.create_user(username=AUTHOR_USERNAME)
        cls.group = Group.objects.create(
            title=GROUP_TITLE,
            slug=GROUP_SLUG,
            description=GROUP_DESCRIPTION,
        )
        Post.objects.bulk_create([
            Post(
                text=f'Тестовый текст {i}',
                author=cls.author_user,
                group=cls.group
            ) for i in range(POSTS_PER_PAGE + 1)
        ])

        cls.urls = [
            INDEX_URL,
            GROUP_LIST_URL,
            PROFILE_URL,
        ]
        cls.guest = Client()

    def test_paginator_first_page(self):
        for url in self.urls:
            with self.subTest(url=url):
                response = self.guest.get(url)
                self.assertEqual(len(response.context['page_obj']),
                                 POSTS_PER_PAGE)

    def test_paginator_second_page(self):
        for url in self.urls:
            with self.subTest(url=url):
                response = self.guest.get(url + '?page=2')
                self.assertEqual(len(response.context['page_obj']), 1)
