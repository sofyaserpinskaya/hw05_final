from django.test import TestCase
from django.urls import reverse


USERNAME = 'TestAuthor'
SLUG = 'test-slug'
POST_ID = 1


class PostsRoutesTests(TestCase):
    def test_url_routes(self):
        urls_routes = [
            ['/', 'index', None],
            [f'/group/{SLUG}/', 'group_list', [SLUG]],
            [f'/profile/{USERNAME}/', 'profile', [USERNAME]],
            [f'/posts/{POST_ID}/', 'post_detail', [POST_ID]],
            ['/create/', 'post_create', None],
            [f'/posts/{POST_ID}/edit/', 'post_edit', [POST_ID]],
            [f'/posts/{POST_ID}/comment', 'add_comment', [POST_ID]],
            ['/follow/', 'follow_index', None],
            [f'/profile/{USERNAME}/follow/', 'profile_follow', [USERNAME]],
            [f'/profile/{USERNAME}/unfollow/', 'profile_unfollow', [USERNAME]],
        ]
        for url, route, parameter in urls_routes:
            with self.subTest(url=url):
                self.assertEqual(url, reverse(
                    f'posts:{route}', args=parameter
                ))
