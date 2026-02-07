const feedList = document.getElementById('feed-list');
const composer = document.getElementById('composer');
const contentInput = document.getElementById('post-content');
const locationInput = document.getElementById('post-location');

const storageKey = 'berendeiPosts';

const defaultPosts = [
  {
    id: 'post-1',
    author: 'Анна Р.',
    location: 'Суздаль',
    content: 'Нашла маршрут по зимнему лесу — делюсь теплом и вдохновением.',
    preview: 'Фото: снежная тропа и горячий чай',
    likes: 842,
    liked: false,
    comments: ['Какая красота!', 'Хочу туда же.'],
    time: '2 часа назад',
  },
  {
    id: 'post-2',
    author: 'Илья М.',
    location: 'Казань',
    content: 'Собрал подборку уютных мест для встреч с друзьями.',
    preview: 'Подборка: лучшие места этой недели',
    likes: 1520,
    liked: false,
    comments: ['Отличные советы!', 'Добавлю в планы.'],
    time: 'Вчера',
  },
];

const loadPosts = () => {
  const saved = localStorage.getItem(storageKey);
  if (!saved) {
    localStorage.setItem(storageKey, JSON.stringify(defaultPosts));
    return [...defaultPosts];
  }
  try {
    const parsed = JSON.parse(saved);
    return Array.isArray(parsed) ? parsed : [...defaultPosts];
  } catch (error) {
    return [...defaultPosts];
  }
};

let posts = loadPosts();

const savePosts = () => {
  localStorage.setItem(storageKey, JSON.stringify(posts));
};

const createPostCard = (post) => {
  const article = document.createElement('article');
  article.className = 'feed-item';
  article.dataset.postId = post.id;

  article.innerHTML = `
    <div class="feed-header">
      <div class="avatar small"></div>
      <div>
        <strong>${post.author}</strong>
        <span>${post.time} · ${post.location || 'Онлайн'}</span>
      </div>
    </div>
    <div class="post-preview">${post.preview}</div>
    <p>${post.content}</p>
    <div class="feed-actions">
      <button type="button" class="like-btn">${post.liked ? '💙' : '❤️'} ${post.likes}</button>
      <span>💬 ${post.comments.length}</span>
      <button type="button" class="share-btn">🔁 Поделиться</button>
    </div>
    <div class="comment-list">
      ${post.comments.map((comment) => `<div>• ${comment}</div>`).join('')}
    </div>
    <form class="comment-form">
      <input type="text" name="comment" placeholder="Написать комментарий..." required />
      <button type="submit">Отправить</button>
    </form>
  `;

  return article;
};

const renderPosts = () => {
  feedList.innerHTML = '';
  posts.forEach((post) => {
    feedList.appendChild(createPostCard(post));
  });
};

const addPost = (event) => {
  event.preventDefault();
  const content = contentInput.value.trim();
  if (!content) return;

  const location = locationInput.value.trim();
  const newPost = {
    id: `post-${Date.now()}`,
    author: 'berendei_official',
    location: location || 'Онлайн',
    content,
    preview: 'Новый пост от вашего аккаунта',
    likes: 0,
    liked: false,
    comments: [],
    time: 'Только что',
  };

  posts = [newPost, ...posts];
  savePosts();
  renderPosts();
  composer.reset();
};

const handleFeedClick = (event) => {
  const card = event.target.closest('.feed-item');
  if (!card) return;
  const postId = card.dataset.postId;
  const post = posts.find((item) => item.id === postId);
  if (!post) return;

  if (event.target.classList.contains('like-btn')) {
    post.liked = !post.liked;
    post.likes += post.liked ? 1 : -1;
    savePosts();
    renderPosts();
  }

  if (event.target.classList.contains('share-btn')) {
    navigator.clipboard?.writeText(`${post.content}`);
    event.target.textContent = '✅ Ссылка скопирована';
    setTimeout(() => {
      event.target.textContent = '🔁 Поделиться';
    }, 1500);
  }
};

const handleCommentSubmit = (event) => {
  if (!event.target.classList.contains('comment-form')) return;
  event.preventDefault();
  const card = event.target.closest('.feed-item');
  if (!card) return;
  const postId = card.dataset.postId;
  const post = posts.find((item) => item.id === postId);
  if (!post) return;
  const input = event.target.querySelector('input[name="comment"]');
  const comment = input.value.trim();
  if (!comment) return;
  post.comments.push(comment);
  savePosts();
  renderPosts();
};

composer.addEventListener('submit', addPost);
feedList.addEventListener('click', handleFeedClick);
feedList.addEventListener('submit', handleCommentSubmit);

renderPosts();
