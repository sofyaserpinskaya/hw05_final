import shutil
import tempfile

from django.conf import settings
from django.core.cache import cache
from django.core.cache.utils import make_template_fragment_key
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from ..models import Comment, Follow, Group, Post, User
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
COMMENT = 'Тестовый комментарий'

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
        cls.comment = Comment.objects.create(
            text=COMMENT,
            post=cls.post,
            author=cls.author_user,
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

    def test_index_follow_profile_grouplist_postdetail_correct_context(self):
        Follow.objects.create(user=self.user, author=self.author_user)
        urls = [
            INDEX_URL,
            FOLLOW_URL,
            GROUP_LIST_URL,
            PROFILE_URL,
            self.POST_DETAIL_URL,
        ]
        for url in urls:
            request = self.another.get(url)
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

    def test_comment_on_post_detail_page_context(self):
        post_comments = self.author.get(
            self.POST_DETAIL_URL).context['post'].comments.all()
        self.assertEqual(len(post_comments), 1)
        post_comment = post_comments[0]
        self.assertEqual(post_comment.text, self.comment.text)
        self.assertEqual(post_comment.author, self.comment.author)
        self.assertEqual(post_comment.post, self.comment.post)

    def test_post_does_not_exist_on_wrong_pages(self):
        urls = [
            GROUP_LIST_2_URL,
            FOLLOW_URL,
        ]
        for url in urls:
            response = self.another.get(url)
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

    def test_follow_author(self):
        self.assertEqual(Follow.objects.count(), 0)
        self.another.get(PROFILE_FOLLOW_URL)
        self.assertEqual(Follow.objects.count(), 1)
        self.assertTrue(Follow.objects.filter(
            user=self.user, author=self.author_user
        ).exists())

    def test_unfollow_author(self):
        self.assertEqual(Follow.objects.count(), 0)
        Follow.objects.create(user=self.user, author=self.author_user)
        self.assertEqual(Follow.objects.count(), 1)
        self.another.get(PROFILE_UNFOLLOW_URL)
        self.assertEqual(Follow.objects.count(), 0)
        self.assertFalse(Follow.objects.filter(
            user=self.user, author=self.author_user
        ).exists())

    def test_cache_index_page(self):
        index_page = self.author.get(INDEX_URL).content
        Post.objects.all().delete()
        self.assertEqual(self.author.get(INDEX_URL).content, index_page)
        cache.delete(make_template_fragment_key('index_page'))
        self.assertNotEqual(self.author.get(INDEX_URL).content, index_page)


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
        cls.guest = Client()

    def test_paginator(self):
        urls_expected_post_number = [
            [INDEX_URL, POSTS_PER_PAGE],
            [GROUP_LIST_URL, POSTS_PER_PAGE],
            [PROFILE_URL, POSTS_PER_PAGE],
            [f'{INDEX_URL}?page=2', 1],
            [f'{GROUP_LIST_URL}?page=2', 1],
            [f'{PROFILE_URL}?page=2', 1],
        ]
        for url, expected_post_number in urls_expected_post_number:
            with self.subTest(url=url):
                response = self.guest.get(url)
                self.assertEqual(len(response.context['page_obj']),
                                 expected_post_number)
