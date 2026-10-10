"""
Загрузка одной волной. Владелец: «сначала одно прогрузилось, потом другое — страница дёргается, такого много».

Отдельный измеритель (волны появления блоков и исчезновения скелетов на первом экране, ответы сервера задержаны
случайно на 0,25–0,9 с) показал:
  - «Избранное» и «Мои объявления»: пока проверялся вход, список уже считался загруженным, и вошедший человек
    видел «пусто» (а в избранном ещё и «войдите»), потом карточки. В избранном вдобавок до прихода списка
    сердечек все карточки отбрасывались как снятые;
  - главная: три волны (истории 1,6 с → разделы 2,4 с → лента 2,7 с) → теперь одна;
  - профиль: шапка, потом баланс, потом кнопка → теперь вместе.
Обход сдвигов после правок: 78 проверок страниц — 0.
"""
from pathlib import Path

SRC = Path(__file__).resolve().parents[2] / "frontend" / "src"


def read(rel):
    return (SRC / rel).read_text(encoding="utf-8")


def test_lists_wait_for_the_login_check_instead_of_showing_empty():
    fav = read("pages/Favorites.jsx")
    assert "if (authLoading) return" in fav and "if (!userId && !authLoading)" in fav and "setLoaded(false)" in fav
    mine = read("pages/MyListings.jsx")
    assert "if (authLoading) return" in mine and "if (initial) setLoaded(false)" in mine and "load(true)" in mine
    assert "if (!user && !authLoading)" in mine


def test_favorites_filter_only_after_the_heart_list_arrived():
    ctx = read("context/FavoritesContext.jsx")
    assert "idsLoaded" in ctx and ".finally(() => setIdsLoaded(true))" in ctx
    assert "idsLoaded ? items.filter((l) => ids.has(l.id)) : items" in read("pages/Favorites.jsx")


def test_home_reveals_stories_categories_and_feed_together_with_a_cap():
    home = read("pages/Home.jsx")
    assert "const firstScreenReady = stories.items !== null && catsLoaded && feedLoaded" in home
    assert "setTimeout(() => setRevealed(true), 1600)" in home
    # истории на главной убраны (шопсы — своей вкладкой); первый экран — разделы и лента, вместе
    assert "if (!catsLoaded || !revealed)" in home and "{!feedLoaded || !revealed" in home


def test_profile_shows_header_balance_and_menu_together_with_a_cap():
    profile = read("pages/Profile.jsx")
    # профиль ждёт и баланс, и цифры («Требует внимания» сдвигала всё на 54 px), не дольше 2,5 с
    assert "onReady={markBalanceReady}" in profile and "setBalanceReady(true); setBalanceTimeout(true) }, 2500)" in profile
    assert "balanceReady && statsLoaded ? 'profile-reveal' : 'profile-hold'" in profile
    assert "if (wallet && onReady) onReady()" in read("components/BalanceCard.jsx")
    css = read("styles.css")
    assert ".profile-hold{ position:absolute; left:0; right:0; visibility:hidden;" in css
