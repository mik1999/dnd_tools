<h1>DnD tools bot</h1>

<em>Поможет любителям Dungeon and Dragons, в первую очередь мастеру подземелий</em>

Написать боту <a href="https://t.me/dnd_tools_bot"> @dnd_tools_bot </a>

<h2> Что сейчас умеет бот? </h2>

<h3>Броски костей</h3>

Простой, но полезный и удобный инструмент и для игрока, и для мастера. Все стандартные кости имеются в виде кнопок. Также парсер умеет обрабатывать сложные ДнД-шные выражения вроде <code>2d10+d6+4</code> и сэмплировать из соответствующего распределения. Для описанного выражения выведенный результат может получиться <code>19 = 12(4+8) + 3 + 4</code>. 

<h3>Авторская алхимия</h3>

Это авторская вариация алхимии, которая предлагает мастеру разнообразить игру, добавив различные ингредиенты зелий, которые игроки смогут каким-либо образом получать и готовить из них полезные зелья. Бот позволяет на ходу определять результат смешивания ингредиентов, а также сохранять результаты и воспроизводить их.

О механике зельеварения можно узнать у бота по двум кнопкам (см. далее). Ниже перечислены возможные на данный момень действия:

<ul>
    <li> <strong> Алхимия > Что это такое?</strong> - Общая информация о зельварении. </li>
    <li> <strong> Алхимия > Параметры > {название_параметра} </strong> - Вывести информацию о параметре зелий, таком как Сила. </li>
    <li> <strong> Алхимия > Ингредиенты > Список ингредиентов </strong> - Вывести список ингредиентов (который будет довольно большой) </li>
    <li> <strong> Алхимия > Ингредиенты > Об ингредиенте </strong> - Поиск информации об ингредиенте. Бот ищет по префиксу и исправляет опечатки. </li>
    <li> <strong> Алхимия > Зелья > Мои зелья </strong> - Здесь можно ввести название своего зелья, чтобы получить о нем информацию. Для последних просмотренных зелий появляются кнопки-подсказки. Также можно попросить вывести весь список зелий. </li>
    <li> <strong> Алхимия > Зелья > Мои зелья > {название_зелья} </strong> - Выводит информацию о зелье, а также позволяет удалить его или сэмплировать случайные эффекты. </li>
    <li> <strong> Алхимия > Зелья > Готовить </strong> - Здесь можно перечислить ингредиенты и получить информацию о получившемся. Далее можно сохранить зелье (где будет предложено ввести название) или готовить дальще. </li>
    <li> <strong> Алхимия > Зелья > Что это такое? </strong> - Информация о готовке зелий. </li>
    <li> <strong> Алхимия > Вывести список ингредиентов </strong> - Выводит список ингредиентов с перечислением параметров, которые они затрагивают. Удобно нажать эту кнопку перед готовкой зелья. </li>
</ul>

<h3>Генераторы</h3>

Классика жанра. Сейчас есть следующий генераторы:
<ul>
    <li> <strong> Имена.  </strong> Имена честно взяты из книги игрока. Можно выбирать расу и пол, а можно и эти параметры сделать случайными. </li>
    <li> <strong> Таверны. </strong> Неожиданно очень удачный генератор. Выдает названия таверны (например "Латунный котелок") + имя и расу хозяина/хозяйки. </li>
    <li> <strong> Волна дикой магии. </strong> Просто эффект дикой магии, который могут вызывать чародеи при использовании заклинаний. </li>
</ul>

<h3>Бестиарий</h3>
Пока что живёт в разделе "генераторы". Довольно внушительный список монстров и прочих существ из вселенной ДнД. Для всех имеются данные об основных характеристиках. Для многих можно загрузить картинку. Также есть возможность сэмплировать атаки (сразу кидается кость атаки, прибавляется модификатор и кидаются все кости урона).

<h2>Как воспроизвести</h2>
Для установки необходимо иметь Docker Compose, аккаунт в телеграме и доступ в интернет. Существующие сети докера не должны конфликтовать с <code>172.20.56.0/24</code> .
<ol>
    <li> Склонировать репозиторий <a href="https://github.com/mik1999/dndexit_tools"> github.com/mik1999/dnd_tools </a>;</li>
    <li> Написать телеграм-боту <a href="https://t.me/BotFather">@BotFather </a>, создать нового бота и сохранить полученный от BotFather токен как dnd_tools/bot/token ;   </li>
    <li> Из рабочей директории dnd_tools (где лежит docker- .yaml) выполнить <code>docker-compose up --build -d</code> ; </li>
</ol>

<h2> Пара слов об архитектуре </h2>
Запускаются два контейнера: один - это mongodb для хранения зелий пользователей, и второй - контейнер с собственно ботом, основанный на образе python:3.7-slim-buster. Контейнеры общаются по сети типа bridge. Бот написан на основе python библиотеки PyTelegramBotAPI.

<h2>Техническая информация</h2>
<h3>Подключение к mongo</h3>
<ol>
    <li><code>docker exec -it mongodb-container bash</code></li>
    <li><code>mongo admin -u dnd_telegram_bot -p f249f9Gty2793f20nD2330ry8432</code></li>
    <li><code>use dnd</code></li>
</ol>
<h3>Подключение к redis</h3>
<ol>
    <li><code>docker exec -it redis-container bash</code></li>
    <li><code>redis-cli</code></li>
    <li><code>get key</code></li>
</ol>

