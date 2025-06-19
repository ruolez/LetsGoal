// Dashboard JavaScript

console.log('🚀 Dashboard.js is loading...'); // Debug log

// Utility function to parse date strings as local dates (fixes timezone issues)
function parseLocalDate(dateString) {
    if (!dateString) return null;
    
    // Handle ISO datetime strings (YYYY-MM-DDTHH:mm:ss) - preserve time for sorting
    if (typeof dateString === 'string' && dateString.includes('T')) {
        // For full datetime strings, use standard Date parsing to preserve time
        return new Date(dateString);
    }
    
    // Handle ISO date strings (YYYY-MM-DD only) 
    if (typeof dateString === 'string' && dateString.includes('-')) {
        const parts = dateString.split('-');
        if (parts.length === 3) {
            const year = parseInt(parts[0]);
            const month = parseInt(parts[1]) - 1; // Month is 0-indexed in JavaScript
            const day = parseInt(parts[2]);
            
            // Validate the date parts
            if (!isNaN(year) && !isNaN(month) && !isNaN(day)) {
                return new Date(year, month, day);
            }
        }
    }
    
    // Fallback to standard Date parsing
    return new Date(dateString);
}

let currentUser = null;
let goals = [];
let tags = [];
let progressChart = null;
let filteredGoals = [];
let currentViewMode = 'grid';
let currentFilter = 'all';
let currentSort = 'recent';
let currentTagFilter = null; // null means show all tags
let selectedTagIds = [];
let currentPage = 0;
const goalsPerPage = 9;

// Track which goal cards should maintain sticky hover state
let stickyHoverStates = new Map();

// ========================
//   THEME MANAGEMENT
// ========================

// Theme management system
function initializeTheme() {
    // Check for stored theme preference or system preference
    const storedTheme = localStorage.getItem('theme');
    const systemPrefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
    
    let theme = 'light'; // default
    if (storedTheme) {
        theme = storedTheme;
    } else if (systemPrefersDark) {
        theme = 'dark';
    }
    
    setTheme(theme);
    
    // Listen for system theme changes
    window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', (e) => {
        // Only auto-switch if user hasn't manually set a preference
        if (!localStorage.getItem('theme')) {
            setTheme(e.matches ? 'dark' : 'light');
        }
    });
}

function setTheme(theme) {
    const html = document.documentElement;
    const themeToggle = document.getElementById('theme-toggle');
    const lightIcon = document.getElementById('theme-icon-light');
    const darkIcon = document.getElementById('theme-icon-dark');
    const themeLabel = document.getElementById('theme-label');
    
    if (theme === 'dark') {
        html.setAttribute('data-theme', 'dark');
        if (lightIcon) lightIcon.classList.add('hidden');
        if (darkIcon) darkIcon.classList.remove('hidden');
        if (themeLabel) themeLabel.textContent = 'Light';
        if (themeToggle) themeToggle.setAttribute('title', 'Switch to light mode');
    } else {
        html.setAttribute('data-theme', 'light');
        if (lightIcon) lightIcon.classList.remove('hidden');
        if (darkIcon) darkIcon.classList.add('hidden');
        if (themeLabel) themeLabel.textContent = 'Dark';
        if (themeToggle) themeToggle.setAttribute('title', 'Switch to dark mode');
    }
    
    // Store the preference
    localStorage.setItem('theme', theme);
}

function toggleTheme() {
    const currentTheme = document.documentElement.getAttribute('data-theme') || 'light';
    const newTheme = currentTheme === 'dark' ? 'light' : 'dark';
    setTheme(newTheme);
}

// Make theme functions globally accessible
window.toggleTheme = toggleTheme;
window.setTheme = setTheme;
window.initializeTheme = initializeTheme;

// ========================
// SETTINGS PERSISTENCE
// ========================

// Default user preferences
const DEFAULT_SETTINGS = {
    viewMode: 'grid',
    filter: 'all',
    sort: 'recent',
    tagFilter: null,
    page: 0,
    searchTerm: ''
};

// Save user settings to localStorage
function saveUserSettings() {
    try {
        const searchInput = document.getElementById('goal-search');
        const searchTerm = searchInput ? searchInput.value : '';
        
        const settings = {
            viewMode: currentViewMode,
            filter: currentFilter,
            sort: currentSort,
            tagFilter: currentTagFilter,
            page: currentPage,
            searchTerm: searchTerm
        };
        
        localStorage.setItem('letsgoal_user_settings', JSON.stringify(settings));
        console.log('💾 User settings saved:', settings);
    } catch (error) {
        console.error('❌ Failed to save user settings:', error);
    }
}

// Load user settings from localStorage
function loadUserSettings() {
    try {
        const saved = localStorage.getItem('letsgoal_user_settings');
        if (saved) {
            const settings = JSON.parse(saved);
            console.log('📂 Loading saved user settings:', settings);
            
            // Apply saved settings
            currentViewMode = settings.viewMode || DEFAULT_SETTINGS.viewMode;
            currentFilter = settings.filter || DEFAULT_SETTINGS.filter;
            currentSort = settings.sort || DEFAULT_SETTINGS.sort;
            currentTagFilter = settings.tagFilter || DEFAULT_SETTINGS.tagFilter;
            currentPage = settings.page || DEFAULT_SETTINGS.page;
            
            // Apply search term
            const searchInput = document.getElementById('goal-search');
            if (searchInput && settings.searchTerm) {
                searchInput.value = settings.searchTerm;
            }
            
            console.log('✅ User settings applied');
            return true;
        } else {
            console.log('📝 No saved settings found, using defaults');
            return false;
        }
    } catch (error) {
        console.error('❌ Failed to load user settings:', error);
        // Reset to defaults on error
        currentViewMode = DEFAULT_SETTINGS.viewMode;
        currentFilter = DEFAULT_SETTINGS.filter;
        currentSort = DEFAULT_SETTINGS.sort;
        currentTagFilter = DEFAULT_SETTINGS.tagFilter;
        currentPage = DEFAULT_SETTINGS.page;
        return false;
    }
}

// Clear user settings (useful for reset)
function clearUserSettings() {
    try {
        localStorage.removeItem('letsgoal_user_settings');
        console.log('🗑️ User settings cleared');
    } catch (error) {
        console.error('❌ Failed to clear user settings:', error);
    }
}

// Apply saved settings to UI elements
function applySettingsToUI() {
    console.log('🎨 Applying settings to UI...');
    
    // Apply view mode
    const viewToggle = document.getElementById('view-toggle');
    if (viewToggle) {
        const isGrid = currentViewMode === 'grid';
        viewToggle.querySelector('.fa-th-large').style.opacity = isGrid ? '1' : '0.5';
        viewToggle.querySelector('.fa-list').style.opacity = isGrid ? '0.5' : '1';
    }
    
    // Apply filter
    const filterLabel = document.getElementById('filter-label');
    if (filterLabel) {
        const filterText = {
            'all': 'All Goals',
            'created': 'Created',
            'started': 'Started',
            'working': 'Working',
            'completed': 'Completed'
        };
        filterLabel.textContent = filterText[currentFilter];
    }
    
    // Apply sort
    const sortLabel = document.getElementById('sort-label');
    if (sortLabel) {
        const sortText = {
            'recent': 'Recently Updated',
            'target': 'Target Date',
            'progress': 'Progress',
            'name': 'Name',
            'urgent_subgoals': 'Due Date'
        };
        sortLabel.textContent = sortText[currentSort];
    }
    
    // Apply tag filter
    const tagFilterLabel = document.getElementById('tag-filter-label');
    if (tagFilterLabel) {
        if (currentTagFilter) {
            const selectedTag = tags.find(tag => tag.id === currentTagFilter);
            if (selectedTag) {
                tagFilterLabel.textContent = selectedTag.name;
            }
        } else {
            tagFilterLabel.textContent = 'All Tags';
        }
    }
    
    console.log('✅ Settings applied to UI');
}

// Dashboard functionality confirmed working

// 365 Inspirational quotes about achieving goals from famous people
const motivationalQuotes = [
    // Business Leaders & Entrepreneurs (Days 1-40)
    {
        text: "The way to get started is to quit talking and begin doing.",
        author: "Walt Disney"
    },
    {
        text: "Innovation distinguishes between a leader and a follower.",
        author: "Steve Jobs"
    },
    {
        text: "Your work is going to fill a large part of your life, and the only way to be truly satisfied is to do what you believe is great work.",
        author: "Steve Jobs"
    },
    {
        text: "The biggest risk is not taking any risk... In a world that's changing quickly, the only strategy that is guaranteed to fail is not taking risks.",
        author: "Mark Zuckerberg"
    },
    {
        text: "Don't be afraid to give up the good to go for the great.",
        author: "John D. Rockefeller"
    },
    {
        text: "The successful warrior is the average man with laser-like focus.",
        author: "Bruce Lee"
    },
    {
        text: "I have not failed. I've just found 10,000 ways that won't work.",
        author: "Thomas Edison"
    },
    {
        text: "Genius is one percent inspiration and ninety-nine percent perspiration.",
        author: "Thomas Edison"
    },
    {
        text: "Many of life's failures are people who did not realize how close they were to success when they gave up.",
        author: "Thomas Edison"
    },
    {
        text: "The whole secret of a successful life is to find out what is one's destiny to do, and then do it.",
        author: "Henry Ford"
    },
    {
        text: "Whether you think you can or you think you can't, you're right.",
        author: "Henry Ford"
    },
    {
        text: "Coming together is a beginning; keeping together is progress; working together is success.",
        author: "Henry Ford"
    },
    {
        text: "Quality means doing it right when no one is looking.",
        author: "Henry Ford"
    },
    {
        text: "Obstacles are those frightful things you see when you take your eyes off your goal.",
        author: "Henry Ford"
    },
    {
        text: "The secret of change is to focus all of your energy not on fighting the old, but on building the new.",
        author: "Socrates"
    },
    {
        text: "I can accept failure, everyone fails at something. But I can't accept not trying.",
        author: "Michael Jordan"
    },
    {
        text: "Talent wins games, but teamwork and intelligence win championships.",
        author: "Michael Jordan"
    },
    {
        text: "I've missed more than 9000 shots in my career. I've lost almost 300 games. 26 times, I've been trusted to take the game winning shot and missed. I've failed over and over and over again in my life. And that is why I succeed.",
        author: "Michael Jordan"
    },
    {
        text: "Some people want it to happen, some wish it would happen, others make it happen.",
        author: "Michael Jordan"
    },
    {
        text: "Don't let what you cannot do interfere with what you can do.",
        author: "John Wooden"
    },
    {
        text: "Success is peace of mind, which is a direct result of self-satisfaction in knowing you made the effort to become the best of which you are capable.",
        author: "John Wooden"
    },
    {
        text: "The difference between a successful person and others is not a lack of strength, not a lack of knowledge, but rather a lack in will.",
        author: "Vince Lombardi"
    },
    {
        text: "Winners never quit and quitters never win.",
        author: "Vince Lombardi"
    },
    {
        text: "Perfection is not attainable, but if we chase perfection we can catch excellence.",
        author: "Vince Lombardi"
    },
    {
        text: "The price of success is hard work, dedication to the job at hand, and the determination that whether we win or lose, we have applied the best of ourselves to the task at hand.",
        author: "Vince Lombardi"
    },
    {
        text: "Individual commitment to a group effort – that is what makes a team work, a company work, a society work, a civilization work.",
        author: "Vince Lombardi"
    },
    {
        text: "If you want something you've never had, you must be willing to do something you've never done.",
        author: "Thomas Jefferson"
    },
    {
        text: "I'm a great believer in luck, and I find the harder I work, the more I have of it.",
        author: "Thomas Jefferson"
    },
    {
        text: "Nothing can stop the man with the right mental attitude from achieving his goal; nothing on earth can help the man with the wrong mental attitude.",
        author: "Thomas Jefferson"
    },
    {
        text: "Do what you can, with what you have, where you are.",
        author: "Theodore Roosevelt"
    },
    {
        text: "It is not the critic who counts; not the man who points out how the strong man stumbles, or where the doer of deeds could have done them better. The credit belongs to the man who is actually in the arena.",
        author: "Theodore Roosevelt"
    },
    {
        text: "Believe you can and you're halfway there.",
        author: "Theodore Roosevelt"
    },
    {
        text: "The only man who never makes a mistake is the man who never does anything.",
        author: "Theodore Roosevelt"
    },
    {
        text: "Far and away the best prize that life offers is the chance to work hard at work worth doing.",
        author: "Theodore Roosevelt"
    },

    // Historical Figures & Presidents (Days 41-80)
    {
        text: "Success consists of going from failure to failure without loss of enthusiasm.",
        author: "Winston Churchill"
    },
    {
        text: "The pessimist sees difficulty in every opportunity. The optimist sees opportunity in every difficulty.",
        author: "Winston Churchill"
    },
    {
        text: "Never give in--never, never, never, never, in nothing great or small, large or petty, never give in except to convictions of honour and good sense.",
        author: "Winston Churchill"
    },
    {
        text: "Kites rise highest against the wind, not with it.",
        author: "Winston Churchill"
    },
    {
        text: "Attitude is a little thing that makes a big difference.",
        author: "Winston Churchill"
    },
    {
        text: "The empires of the future are the empires of the mind.",
        author: "Winston Churchill"
    },
    {
        text: "Success is not final, failure is not fatal: it is the courage to continue that counts.",
        author: "Winston Churchill"
    },
    {
        text: "You have power over your mind - not outside events. Realize this, and you will find strength.",
        author: "Marcus Aurelius"
    },
    {
        text: "The best revenge is not to be like your enemy.",
        author: "Marcus Aurelius"
    },
    {
        text: "Very little is needed to make a happy life; it is all within yourself, in your way of thinking.",
        author: "Marcus Aurelius"
    },
    {
        text: "What we do now echoes in eternity.",
        author: "Marcus Aurelius"
    },
    {
        text: "If you want to improve, be content to be thought foolish and stupid with regard to external things.",
        author: "Epictetus"
    },
    {
        text: "No man is free who is not master of himself.",
        author: "Epictetus"
    },
    {
        text: "It's not what happens to you, but how you react to it that matters.",
        author: "Epictetus"
    },
    {
        text: "First say to yourself what you would be; and then do what you have to do.",
        author: "Epictetus"
    },
    {
        text: "Nearly all men can stand adversity, but if you want to test a man's character, give him power.",
        author: "Abraham Lincoln"
    },
    {
        text: "Whatever you are, be a good one.",
        author: "Abraham Lincoln"
    },
    {
        text: "I am a slow walker, but I never walk back.",
        author: "Abraham Lincoln"
    },
    {
        text: "The best way to predict your future is to create it.",
        author: "Abraham Lincoln"
    },
    {
        text: "My great concern is not whether you have failed, but whether you are content with your failure.",
        author: "Abraham Lincoln"
    },
    {
        text: "Give me six hours to chop down a tree and I will spend the first four sharpening the axe.",
        author: "Abraham Lincoln"
    },
    {
        text: "Most folks are as happy as they make up their minds to be.",
        author: "Abraham Lincoln"
    },
    {
        text: "Ask not what your country can do for you – ask what you can do for your country.",
        author: "John F. Kennedy"
    },
    {
        text: "Efforts and courage are not enough without purpose and direction.",
        author: "John F. Kennedy"
    },
    {
        text: "Change is the law of life. And those who look only to the past or present are certain to miss the future.",
        author: "John F. Kennedy"
    },
    {
        text: "Leadership and learning are indispensable to each other.",
        author: "John F. Kennedy"
    },
    {
        text: "Let us not seek the Republican answer or the Democratic answer, but the right answer.",
        author: "John F. Kennedy"
    },
    {
        text: "The Chinese use two brush strokes to write the word 'crisis.' One brush stroke stands for danger; the other for opportunity.",
        author: "John F. Kennedy"
    },
    {
        text: "As we express our gratitude, we must never forget that the highest appreciation is not to utter words, but to live by them.",
        author: "John F. Kennedy"
    },
    {
        text: "Conformity is the jailer of freedom and the enemy of growth.",
        author: "John F. Kennedy"
    },
    {
        text: "The time to repair the roof is when the sun is shining.",
        author: "John F. Kennedy"
    },
    {
        text: "Energy and persistence conquer all things.",
        author: "Benjamin Franklin"
    },
    {
        text: "An investment in knowledge pays the best interest.",
        author: "Benjamin Franklin"
    },
    {
        text: "Tell me and I forget, teach me and I may remember, involve me and I learn.",
        author: "Benjamin Franklin"
    },
    {
        text: "Well done is better than well said.",
        author: "Benjamin Franklin"
    },
    {
        text: "By failing to prepare, you are preparing to fail.",
        author: "Benjamin Franklin"
    },
    {
        text: "Either write something worth reading or do something worth writing.",
        author: "Benjamin Franklin"
    },
    {
        text: "Hide not your talents, they for use were made. What's a sundial in the shade?",
        author: "Benjamin Franklin"
    },
    {
        text: "The Constitution only gives people the right to pursue happiness. You have to catch it yourself.",
        author: "Benjamin Franklin"
    },
    {
        text: "It is during our darkest moments that we must focus to see the light.",
        author: "Aristotle"
    },
    {
        text: "Excellence is never an accident. It is always the result of high intention, sincere effort, and intelligent execution.",
        author: "Aristotle"
    },

    // Civil Rights Leaders & Social Activists (Days 81-100)
    {
        text: "The ultimate measure of a man is not where he stands in moments of comfort and convenience, but where he stands at times of challenge and controversy.",
        author: "Martin Luther King Jr."
    },
    {
        text: "Darkness cannot drive out darkness; only light can do that. Hate cannot drive out hate; only love can do that.",
        author: "Martin Luther King Jr."
    },
    {
        text: "Faith is taking the first step even when you don't see the whole staircase.",
        author: "Martin Luther King Jr."
    },
    {
        text: "If you can't fly then run, if you can't run then walk, if you can't walk then crawl, but whatever you do you have to keep moving forward.",
        author: "Martin Luther King Jr."
    },
    {
        text: "Life's most persistent and urgent question is: 'What are you doing for others?'",
        author: "Martin Luther King Jr."
    },
    {
        text: "Intelligence plus character-that is the goal of true education.",
        author: "Martin Luther King Jr."
    },
    {
        text: "We must accept finite disappointment, but never lose infinite hope.",
        author: "Martin Luther King Jr."
    },
    {
        text: "Be yourself; everyone else is already taken.",
        author: "Oscar Wilde"
    },
    {
        text: "We are all in the gutter, but some of us are looking at the stars.",
        author: "Oscar Wilde"
    },
    {
        text: "I can resist everything except temptation.",
        author: "Oscar Wilde"
    },
    {
        text: "Experience is merely the name men gave to their mistakes.",
        author: "Oscar Wilde"
    },
    {
        text: "No one can make you feel inferior without your consent.",
        author: "Eleanor Roosevelt"
    },
    {
        text: "The future belongs to those who believe in the beauty of their dreams.",
        author: "Eleanor Roosevelt"
    },
    {
        text: "You must do the things you think you cannot do.",
        author: "Eleanor Roosevelt"
    },
    {
        text: "It is better to light a candle than curse the darkness.",
        author: "Eleanor Roosevelt"
    },
    {
        text: "Great minds discuss ideas; average minds discuss events; small minds discuss people.",
        author: "Eleanor Roosevelt"
    },
    {
        text: "You gain strength, courage, and confidence by every experience in which you really stop to look fear in the face.",
        author: "Eleanor Roosevelt"
    },
    {
        text: "The purpose of life is not to be happy. It is to be useful, to be honorable, to be compassionate, to have it make some difference that you have lived and lived well.",
        author: "Ralph Waldo Emerson"
    },
    {
        text: "Do not go where the path may lead, go instead where there is no path and leave a trail.",
        author: "Ralph Waldo Emerson"
    },
    {
        text: "What you do speaks so loudly that I cannot hear what you say.",
        author: "Ralph Waldo Emerson"
    },
    {
        text: "The only way to have a friend is to be one.",
        author: "Ralph Waldo Emerson"
    },

    // Scientists & Inventors (Days 101-140)
    {
        text: "Imagination is more important than knowledge.",
        author: "Albert Einstein"
    },
    {
        text: "Try not to become a person of success, but rather try to become a person of value.",
        author: "Albert Einstein"
    },
    {
        text: "It is not that I'm so smart. But I stay with the questions much longer.",
        author: "Albert Einstein"
    },
    {
        text: "Great spirits have always encountered violent opposition from mediocre minds.",
        author: "Albert Einstein"
    },
    {
        text: "Learn from yesterday, live for today, hope for tomorrow. The important thing is not to stop questioning.",
        author: "Albert Einstein"
    },
    {
        text: "Logic will get you from A to B. Imagination will take you everywhere.",
        author: "Albert Einstein"
    },
    {
        text: "A person who never made a mistake never tried anything new.",
        author: "Albert Einstein"
    },
    {
        text: "The important thing is not to stop questioning. Curiosity has its own reason for existing.",
        author: "Albert Einstein"
    },
    {
        text: "Weakness of attitude becomes weakness of character.",
        author: "Albert Einstein"
    },
    {
        text: "In the middle of difficulty lies opportunity.",
        author: "Albert Einstein"
    },
    {
        text: "Life is like riding a bicycle. To keep your balance, you must keep moving.",
        author: "Albert Einstein"
    },
    {
        text: "Once we accept our limits, we go beyond them.",
        author: "Albert Einstein"
    },
    {
        text: "Peace cannot be kept by force; it can only be achieved by understanding.",
        author: "Albert Einstein"
    },
    {
        text: "Strive not to be a success, but rather to be of value.",
        author: "Albert Einstein"
    },
    {
        text: "The true sign of intelligence is not knowledge but imagination.",
        author: "Albert Einstein"
    },
    {
        text: "Our greatest weakness lies in giving up. The most certain way to succeed is always to try just one more time.",
        author: "Thomas Edison"
    },
    {
        text: "Opportunity is missed by most people because it is dressed in overalls and looks like work.",
        author: "Thomas Edison"
    },
    {
        text: "There's a way to do it better - find it.",
        author: "Thomas Edison"
    },
    {
        text: "I find out what the world needs. Then I go ahead and try to invent it.",
        author: "Thomas Edison"
    },
    {
        text: "The three great essentials to achieve anything worthwhile are: Hard work, Stick-to-itiveness, and Common sense.",
        author: "Thomas Edison"
    },
    {
        text: "Results! Why, man, I have gotten a lot of results. I know several thousand ways that won't work.",
        author: "Thomas Edison"
    },
    {
        text: "Everything comes to him who hustles while he waits.",
        author: "Thomas Edison"
    },
    {
        text: "The doctor of the future will give no medicine, but will interest his patients in the care of the human frame, in diet, and in the cause and prevention of disease.",
        author: "Thomas Edison"
    },
    {
        text: "To invent, you need a good imagination and a pile of junk.",
        author: "Thomas Edison"
    },
    {
        text: "Being busy does not always mean real work. The object of all work is production or accomplishment.",
        author: "Thomas Edison"
    },
    {
        text: "Non-violence is a weapon of the strong.",
        author: "Mahatma Gandhi"
    },
    {
        text: "Be the change that you wish to see in the world.",
        author: "Mahatma Gandhi"
    },
    {
        text: "Live as if you were to die tomorrow. Learn as if you were to live forever.",
        author: "Mahatma Gandhi"
    },
    {
        text: "The weak can never forgive. Forgiveness is the attribute of the strong.",
        author: "Mahatma Gandhi"
    },
    {
        text: "Happiness is when what you think, what you say, and what you do are in harmony.",
        author: "Mahatma Gandhi"
    },
    {
        text: "In a gentle way, you can shake the world.",
        author: "Mahatma Gandhi"
    },
    {
        text: "The best way to find yourself is to lose yourself in the service of others.",
        author: "Mahatma Gandhi"
    },
    {
        text: "An eye for an eye only ends up making the whole world blind.",
        author: "Mahatma Gandhi"
    },
    {
        text: "First they ignore you, then they laugh at you, then they fight you, then you win.",
        author: "Mahatma Gandhi"
    },
    {
        text: "You must be the change you wish to see in the world.",
        author: "Mahatma Gandhi"
    },
    {
        text: "It does not matter how slowly you go as long as you do not stop.",
        author: "Confucius"
    },
    {
        text: "Our greatest glory is not in never falling, but in rising every time we fall.",
        author: "Confucius"
    },
    {
        text: "The man who moves a mountain begins by carrying away small stones.",
        author: "Confucius"
    },
    {
        text: "When we see men of worth, we should think of equaling them; when we see men of a contrary character, we should turn inwards and examine ourselves.",
        author: "Confucius"
    },
    {
        text: "Real knowledge is to know the extent of one's ignorance.",
        author: "Confucius"
    },

    // Authors & Writers (Days 141-180)
    {
        text: "The secret of getting ahead is getting started.",
        author: "Mark Twain"
    },
    {
        text: "Courage is resistance to fear, mastery of fear - not absence of fear.",
        author: "Mark Twain"
    },
    {
        text: "If you tell the truth, you don't have to remember anything.",
        author: "Mark Twain"
    },
    {
        text: "The two most important days in your life are the day you are born and the day you find out why.",
        author: "Mark Twain"
    },
    {
        text: "Kindness is the language which the deaf can hear and the blind can see.",
        author: "Mark Twain"
    },
    {
        text: "The best way to cheer yourself up is to try to cheer somebody else up.",
        author: "Mark Twain"
    },
    {
        text: "Don't go around saying the world owes you a living. The world owes you nothing. It was here first.",
        author: "Mark Twain"
    },
    {
        text: "It is better to keep your mouth closed and let people think you are a fool than to open it and remove all doubt.",
        author: "Mark Twain"
    },
    {
        text: "The difference between the almost right word and the right word is really a large matter.",
        author: "Mark Twain"
    },
    {
        text: "Age is an issue of mind over matter. If you don't mind, it doesn't matter.",
        author: "Mark Twain"
    },
    {
        text: "A lie can travel halfway around the world while the truth is putting on its shoes.",
        author: "Mark Twain"
    },
    {
        text: "Good friends, good books, and a sleepy conscience: this is the ideal life.",
        author: "Mark Twain"
    },
    {
        text: "The fear of death follows from the fear of life. A man who lives fully is prepared to die at any time.",
        author: "Mark Twain"
    },
    {
        text: "Everyone is a moon, and has a dark side which he never shows to anybody.",
        author: "Mark Twain"
    },
    {
        text: "Whenever you find yourself on the side of the majority, it is time to pause and reflect.",
        author: "Mark Twain"
    },
    {
        text: "Twenty years from now you will be more disappointed by the things that you didn't do than by the ones you did do.",
        author: "Mark Twain"
    },
    {
        text: "I can live for two months on a good compliment.",
        author: "Mark Twain"
    },
    {
        text: "Success is not final, failure is not fatal: it is the courage to continue that counts.",
        author: "Winston Churchill"
    },
    {
        text: "It is not the size of a man but the size of his heart that matters.",
        author: "Evander Holyfield"
    },
    {
        text: "You have been critical of yourself for years, and it hasn't worked. Try approving of yourself and see what happens.",
        author: "Louise Hay"
    },
    {
        text: "The greatest glory in living lies not in never falling, but in rising every time we fall.",
        author: "Nelson Mandela"
    },
    {
        text: "There is no passion to be found playing small – in settling for a life that is less than the one you are capable of living.",
        author: "Nelson Mandela"
    },
    {
        text: "It always seems impossible until it's done.",
        author: "Nelson Mandela"
    },
    {
        text: "I learned that courage was not the absence of fear, but the triumph over it.",
        author: "Nelson Mandela"
    },
    {
        text: "Education is the most powerful weapon which you can use to change the world.",
        author: "Nelson Mandela"
    },
    {
        text: "A winner is a dreamer who never gives up.",
        author: "Nelson Mandela"
    },
    {
        text: "There can be no keener revelation of a society's soul than the way in which it treats its children.",
        author: "Nelson Mandela"
    },
    {
        text: "If you want to make peace with your enemy, you have to work with your enemy. Then he becomes your partner.",
        author: "Nelson Mandela"
    },
    {
        text: "Money won't create success, the freedom to make it will.",
        author: "Nelson Mandela"
    },
    {
        text: "I never lose. I either win or learn.",
        author: "Nelson Mandela"
    },
    {
        text: "Resentment is like drinking poison and then hoping it will kill your enemies.",
        author: "Nelson Mandela"
    },
    {
        text: "Lead from the back — and let others believe they are in front.",
        author: "Nelson Mandela"
    },
    {
        text: "What counts in life is not the mere fact that we have lived. It is what difference we have made to the lives of others.",
        author: "Nelson Mandela"
    },
    {
        text: "There is nothing like returning to a place that remains unchanged to find the ways in which you yourself have altered.",
        author: "Nelson Mandela"
    },
    {
        text: "If you talk to a man in a language he understands, that goes to his head. If you talk to him in his language, that goes to his heart.",
        author: "Nelson Mandela"
    },
    {
        text: "I am fundamentally an optimist. Whether that comes from nature or nurture, I cannot say.",
        author: "Nelson Mandela"
    },
    {
        text: "For to be free is not merely to cast off one's chains, but to live in a way that respects and enhances the freedom of others.",
        author: "Nelson Mandela"
    },
    {
        text: "Courage is not the absence of fear, but action in spite of it.",
        author: "Nelson Mandela"
    },
    {
        text: "A good head and a good heart are always a formidable combination.",
        author: "Nelson Mandela"
    },
    {
        text: "After climbing a great hill, one only finds that there are many more hills to climb.",
        author: "Nelson Mandela"
    },
    {
        text: "I have walked that long road to freedom. I have tried not to falter; I have made missteps along the way.",
        author: "Nelson Mandela"
    },

    // Modern Leaders & Entrepreneurs (Days 181-220)
    {
        text: "The greatest risk is not taking any risk... In a world that's changing quickly, the only strategy that is guaranteed to fail is not taking risks.",
        author: "Mark Zuckerberg"
    },
    {
        text: "Move fast and break things. Unless you are breaking stuff, you are not moving fast enough.",
        author: "Mark Zuckerberg"
    },
    {
        text: "The biggest risk is not taking any risk.",
        author: "Mark Zuckerberg"
    },
    {
        text: "People can be really smart or have skills that are directly applicable, but if they don't really believe in it, then they are not going to really work hard.",
        author: "Mark Zuckerberg"
    },
    {
        text: "I think a simple rule of business is, if you do the things that are easier first, then you can actually make a lot of progress.",
        author: "Mark Zuckerberg"
    },
    {
        text: "When you want to change things, you can't please everyone. If you do please everyone, you aren't making enough progress.",
        author: "Elon Musk"
    },
    {
        text: "If something is important enough, even if the odds are against you, you should still do it.",
        author: "Elon Musk"
    },
    {
        text: "I think it's very important to have a feedback loop, where you're constantly thinking about what you've done and how you could be doing it better.",
        author: "Elon Musk"
    },
    {
        text: "Persistence is very important. You should not give up unless you are forced to give up.",
        author: "Elon Musk"
    },
    {
        text: "When something is important enough, you do it even if the odds are not in your favor.",
        author: "Elon Musk"
    },
    {
        text: "I could either watch it happen or be a part of it.",
        author: "Elon Musk"
    },
    {
        text: "Failure is an option here. If things are not failing, you are not innovating enough.",
        author: "Elon Musk"
    },
    {
        text: "Some people don't like change, but you need to embrace change if the alternative is disaster.",
        author: "Elon Musk"
    },
    {
        text: "It's OK to have your eggs in one basket as long as you control what happens to that basket.",
        author: "Elon Musk"
    },
    {
        text: "Life is too short for long-term grudges.",
        author: "Elon Musk"
    },
    {
        text: "I don't create companies for the sake of creating companies, but to get things done.",
        author: "Elon Musk"
    },
    {
        text: "The first step is to establish that something is possible; then probability will occur.",
        author: "Elon Musk"
    },
    {
        text: "If you're trying to create a company, it's like baking a cake. You have to have all the ingredients in the right proportion.",
        author: "Elon Musk"
    },
    {
        text: "Really pay attention to negative feedback and solicit it, particularly from friends.",
        author: "Elon Musk"
    },
    {
        text: "Work like hell. I mean you just have to put in 80 to 100 hour weeks every week.",
        author: "Elon Musk"
    },
    {
        text: "Great companies are built on great products.",
        author: "Elon Musk"
    },
    {
        text: "I think it is possible for ordinary people to choose to be extraordinary.",
        author: "Elon Musk"
    },
    {
        text: "Your worth consists in what you are and not in what you have.",
        author: "Thomas Edison"
    },
    {
        text: "Don't let yesterday take up too much of today.",
        author: "Will Rogers"
    },
    {
        text: "You learn more from failure than from success. Don't let it stop you. Failure builds character.",
        author: "Unknown"
    },
    {
        text: "It's not whether you get knocked down, it's whether you get up.",
        author: "Vince Lombardi"
    },
    {
        text: "If you are working on something that you really care about, you don't have to be pushed. The vision pulls you.",
        author: "Steve Jobs"
    },
    {
        text: "People who are crazy enough to think they can change the world, are the ones who do.",
        author: "Rob Siltanen"
    },
    {
        text: "We don't make mistakes, just happy little accidents.",
        author: "Bob Ross"
    },
    {
        text: "Failure will never overtake me if my determination to succeed is strong enough.",
        author: "Og Mandino"
    },
    {
        text: "Entrepreneurs are great at dealing with uncertainty and also very good at minimizing risk. That's the classic entrepreneur.",
        author: "Mohnish Pabrai"
    },
    {
        text: "We may encounter many defeats but we must not be defeated.",
        author: "Maya Angelou"
    },
    {
        text: "Knowing what must be done does away with fear.",
        author: "Rosa Parks"
    },
    {
        text: "I can't change the direction of the wind, but I can adjust my sails to always reach my destination.",
        author: "Jimmy Dean"
    },
    {
        text: "If you look at what you have in life, you'll always have more.",
        author: "Oprah Winfrey"
    },
    {
        text: "What I know for sure is that what you give comes back to you.",
        author: "Oprah Winfrey"
    },
    {
        text: "Everyone wants to ride with you in the limo, but what you want is someone who will take the bus with you when the limo breaks down.",
        author: "Oprah Winfrey"
    },
    {
        text: "Turn your wounds into wisdom.",
        author: "Oprah Winfrey"
    },
    {
        text: "The biggest adventure you can take is to live the life of your dreams.",
        author: "Oprah Winfrey"
    },
    {
        text: "Real integrity is doing the right thing, knowing that nobody's going to know whether you did it or not.",
        author: "Oprah Winfrey"
    },

    // Sports Champions & Athletes (Days 221-260)
    {
        text: "Champions aren't made in gyms. Champions are made from something deep inside them - a desire, a dream, a vision.",
        author: "Muhammad Ali"
    },
    {
        text: "Float like a butterfly, sting like a bee.",
        author: "Muhammad Ali"
    },
    {
        text: "Don't count the days, make the days count.",
        author: "Muhammad Ali"
    },
    {
        text: "It's not bragging if you can back it up.",
        author: "Muhammad Ali"
    },
    {
        text: "Service to others is the rent you pay for your room here on earth.",
        author: "Muhammad Ali"
    },
    {
        text: "If my mind can conceive it, and my heart can believe it—then I can achieve it.",
        author: "Muhammad Ali"
    },
    {
        text: "Impossible is just an opinion.",
        author: "Muhammad Ali"
    },
    {
        text: "He who is not courageous enough to take risks will accomplish nothing in life.",
        author: "Muhammad Ali"
    },
    {
        text: "I hated every minute of training, but I said, 'Don't quit. Suffer now and live the rest of your life as a champion.'",
        author: "Muhammad Ali"
    },
    {
        text: "The man who has no imagination has no wings.",
        author: "Muhammad Ali"
    },
    {
        text: "A man who views the world the same at fifty as he did at twenty has wasted thirty years of his life.",
        author: "Muhammad Ali"
    },
    {
        text: "The fight is won or lost far away from witnesses—behind the lines, in the gym, and out there on the road, long before I dance under those lights.",
        author: "Muhammad Ali"
    },
    {
        text: "To be a great champion you must believe you are the best. If you're not, pretend you are.",
        author: "Muhammad Ali"
    },
    {
        text: "Age is whatever you think it is. You are as old as you think you are.",
        author: "Muhammad Ali"
    },
    {
        text: "I am the greatest, I said that even before I knew I was.",
        author: "Muhammad Ali"
    },
    {
        text: "What keeps me going is goals.",
        author: "Muhammad Ali"
    },
    {
        text: "Only a man who knows what it is like to be defeated can reach down to the bottom of his soul and come up with the extra ounce of power it takes to win when the match is even.",
        author: "Muhammad Ali"
    },
    {
        text: "It isn't the mountains ahead to climb that wear you out; it's the pebble in your shoe.",
        author: "Muhammad Ali"
    },
    {
        text: "I never think of the future - it comes soon enough.",
        author: "Albert Einstein"
    },
    {
        text: "Education is what remains after one has forgotten what one has learned in school.",
        author: "Albert Einstein"
    },
    {
        text: "To be successful you have to be selfish, or else you never achieve. And once you get to your highest level, then you have to be unselfish.",
        author: "Michael Jordan"
    },
    {
        text: "I've always believed that if you put in the work, the results will come.",
        author: "Michael Jordan"
    },
    {
        text: "My attitude is that if you push me towards something that you think is a weakness, then I will turn that perceived weakness into a strength.",
        author: "Michael Jordan"
    },
    {
        text: "I can accept failure, everyone fails at something. But I can't accept not trying.",
        author: "Michael Jordan"
    },
    {
        text: "Obstacles don't have to stop you. If you run into a wall, don't turn around and give up. Figure out how to climb it, go through it, or work around it.",
        author: "Michael Jordan"
    },
    {
        text: "Always turn a negative situation into a positive situation.",
        author: "Michael Jordan"
    },
    {
        text: "If you're trying to achieve, there will be roadblocks. I've had them; everybody has had them. But obstacles don't have to stop you.",
        author: "Michael Jordan"
    },
    {
        text: "Step by step. I can't think of any other way of accomplishing anything.",
        author: "Michael Jordan"
    },
    {
        text: "I've never been afraid to fail.",
        author: "Michael Jordan"
    },
    {
        text: "The game is my wife. It demands loyalty and responsibility, and it gives me back fulfillment and peace.",
        author: "Michael Jordan"
    },
    {
        text: "Champions keep playing until they get it right.",
        author: "Billie Jean King"
    },
    {
        text: "Pressure is a privilege.",
        author: "Billie Jean King"
    },
    {
        text: "I think self-awareness is probably the most important thing towards being a champion.",
        author: "Billie Jean King"
    },
    {
        text: "Victory belongs to the most persevering.",
        author: "Napoleon Bonaparte"
    },
    {
        text: "A leader is a dealer in hope.",
        author: "Napoleon Bonaparte"
    },
    {
        text: "Impossible is a word to be found only in the dictionary of fools.",
        author: "Napoleon Bonaparte"
    },
    {
        text: "The harder the conflict, the more glorious the triumph.",
        author: "Thomas Paine"
    },
    {
        text: "What we obtain too cheap, we esteem too lightly.",
        author: "Thomas Paine"
    },
    {
        text: "I love the man that can smile in trouble, that can gather strength from distress, and grow brave by reflection.",
        author: "Thomas Paine"
    },
    {
        text: "The real man smiles in trouble, gathers strength from distress, and grows brave by reflection.",
        author: "Thomas Paine"
    },

    // Philosophers & Thinkers (Days 261-300)
    {
        text: "The only true wisdom is in knowing you know nothing.",
        author: "Socrates"
    },
    {
        text: "An unexamined life is not worth living.",
        author: "Socrates"
    },
    {
        text: "The only good is knowledge and the only evil is ignorance.",
        author: "Socrates"
    },
    {
        text: "Wonder is the beginning of wisdom.",
        author: "Socrates"
    },
    {
        text: "By all means, marry. If you get a good wife, you'll become happy; if you get a bad one, you'll become a philosopher.",
        author: "Socrates"
    },
    {
        text: "There is only one good, knowledge, and one evil, ignorance.",
        author: "Socrates"
    },
    {
        text: "To find yourself, think for yourself.",
        author: "Socrates"
    },
    {
        text: "Beware the barrenness of a busy life.",
        author: "Socrates"
    },
    {
        text: "Understanding a question is half an answer.",
        author: "Socrates"
    },
    {
        text: "I cannot teach anybody anything. I can only make them think.",
        author: "Socrates"
    },
    {
        text: "He is richest who is content with the least, for content is the wealth of nature.",
        author: "Socrates"
    },
    {
        text: "The way to gain a good reputation is to endeavor to be what you desire to appear.",
        author: "Socrates"
    },
    {
        text: "When the debate is lost, slander becomes the tool of the loser.",
        author: "Socrates"
    },
    {
        text: "Employ your time in improving yourself by other men's writings, so that you shall gain easily what others have labored hard for.",
        author: "Socrates"
    },
    {
        text: "The greatest way to live with honor in this world is to be what we pretend to be.",
        author: "Socrates"
    },
    {
        text: "Smart people learn from everything and everyone, average people from their experiences, stupid people already have all the answers.",
        author: "Socrates"
    },
    {
        text: "Strong minds discuss ideas, average minds discuss events, weak minds discuss people.",
        author: "Socrates"
    },
    {
        text: "If you don't get what you want, you suffer; if you get what you don't want, you suffer.",
        author: "Socrates"
    },
    {
        text: "Sometimes you win, sometimes you learn.",
        author: "John Maxwell"
    },
    {
        text: "A leader is one who knows the way, goes the way, and shows the way.",
        author: "John Maxwell"
    },
    {
        text: "Everything rises and falls on leadership.",
        author: "John Maxwell"
    },
    {
        text: "The greatest mistake we make is living in constant fear that we will make one.",
        author: "John Maxwell"
    },
    {
        text: "People may hear your words, but they feel your attitude.",
        author: "John Maxwell"
    },
    {
        text: "A man must be big enough to admit his mistakes, smart enough to profit from them, and strong enough to correct them.",
        author: "John Maxwell"
    },
    {
        text: "The pessimist complains about the wind. The optimist expects it to change. The leader adjusts the sails.",
        author: "John Maxwell"
    },
    {
        text: "Change is inevitable. Growth is optional.",
        author: "John Maxwell"
    },
    {
        text: "Leadership is not about titles, positions or flowcharts. It is about one life influencing another.",
        author: "John Maxwell"
    },
    {
        text: "The secret of your success is determined by your daily agenda.",
        author: "John Maxwell"
    },
    {
        text: "We cannot become what we need to be by remaining what we are.",
        author: "John Maxwell"
    },
    {
        text: "You'll never change your life until you change something you do daily.",
        author: "John Maxwell"
    },
    {
        text: "Dreams don't work unless you do.",
        author: "John Maxwell"
    },
    {
        text: "If you want to do a few small things right, do them yourself. If you want to do great things and make a big impact, learn to delegate.",
        author: "John Maxwell"
    },
    {
        text: "Most people want to avoid pain, and discipline is usually painful.",
        author: "John Maxwell"
    },
    {
        text: "The difference between average people and achieving people is their perception of and response to failure.",
        author: "John Maxwell"
    },
    {
        text: "If you are not making the progress that you would like to make and are capable of making, it is simply because your goals are not clearly defined.",
        author: "Paul Meyer"
    },
    {
        text: "Whatever you vividly imagine, ardently desire, sincerely believe, and enthusiastically act upon must inevitably come to pass!",
        author: "Paul Meyer"
    },
    {
        text: "Productivity is never an accident. It is always the result of a commitment to excellence, intelligent planning, and focused effort.",
        author: "Paul Meyer"
    },
    {
        text: "Determine what specific goal you want to achieve. Then dedicate yourself to its attainment with unswerving singleness of purpose, the trenchant zeal of a crusader.",
        author: "Paul Meyer"
    },

    // Modern Visionaries & CEOs (Days 301-340)
    {
        text: "If I'd asked customers what they wanted, they would have said a faster horse.",
        author: "Henry Ford"
    },
    {
        text: "Failure is simply the opportunity to begin again, this time more intelligently.",
        author: "Henry Ford"
    },
    {
        text: "Thinking is the hardest work there is, which is probably the reason why so few engage in it.",
        author: "Henry Ford"
    },
    {
        text: "Anyone who stops learning is old, whether at twenty or eighty. Anyone who keeps learning stays young.",
        author: "Henry Ford"
    },
    {
        text: "Don't find fault, find a remedy; anybody can complain.",
        author: "Henry Ford"
    },
    {
        text: "Most people spend more time and energy going around problems than in trying to solve them.",
        author: "Henry Ford"
    },
    {
        text: "If everyone is moving forward together, then success takes care of itself.",
        author: "Henry Ford"
    },
    {
        text: "The only real mistake is the one from which we learn nothing.",
        author: "Henry Ford"
    },
    {
        text: "A business that makes nothing but money is a poor business.",
        author: "Henry Ford"
    },
    {
        text: "Vision without execution is just hallucination.",
        author: "Henry Ford"
    },
    {
        text: "I will build a car for the great multitude.",
        author: "Henry Ford"
    },
    {
        text: "If you always do what interests you, at least one person is pleased.",
        author: "Katharine Hepburn"
    },
    {
        text: "The time for action is now. It's never too late to do something.",
        author: "Antoine de Saint-Exupéry"
    },
    {
        text: "A goal is not always meant to be reached, it often serves simply as something to aim at.",
        author: "Bruce Lee"
    },
    {
        text: "Do not pray for easy lives. Pray to be stronger men.",
        author: "John F. Kennedy"
    },
    {
        text: "In the end, we will remember not the words of our enemies, but the silence of our friends.",
        author: "Martin Luther King Jr."
    },
    {
        text: "If you want to lift yourself up, lift up someone else.",
        author: "Booker T. Washington"
    },
    {
        text: "Excellence is never an accident. It is always the result of high intention, sincere effort, and intelligent execution; it represents the wise choice of many alternatives.",
        author: "Aristotle"
    },
    {
        text: "We are what we repeatedly do. Excellence, then, is not an act, but a habit.",
        author: "Aristotle"
    },
    {
        text: "There is only one way to avoid criticism: do nothing, say nothing, and be nothing.",
        author: "Aristotle"
    },
    {
        text: "Knowing yourself is the beginning of all wisdom.",
        author: "Aristotle"
    },
    {
        text: "The roots of education are bitter, but the fruit is sweet.",
        author: "Aristotle"
    },
    {
        text: "Quality is not an act, it is a habit.",
        author: "Aristotle"
    },
    {
        text: "The whole is greater than the sum of its parts.",
        author: "Aristotle"
    },
    {
        text: "Pleasure in the job puts perfection in the work.",
        author: "Aristotle"
    },
    {
        text: "Hope is a waking dream.",
        author: "Aristotle"
    },
    {
        text: "The aim of art is to represent not the outward appearance of things, but their inward significance.",
        author: "Aristotle"
    },
    {
        text: "Educating the mind without educating the heart is no education at all.",
        author: "Aristotle"
    },
    {
        text: "Patience is bitter, but its fruit is sweet.",
        author: "Aristotle"
    },
    {
        text: "The educated differ from the uneducated as much as the living differ from the dead.",
        author: "Aristotle"
    },

    // Wisdom & Final Inspirations (Days 341-365)
    {
        text: "Be yourself; everyone else is already taken.",
        author: "Oscar Wilde"
    },
    {
        text: "Two things are infinite: the universe and human stupidity; and I'm not sure about the universe.",
        author: "Albert Einstein"
    },
    {
        text: "So many books, so little time.",
        author: "Frank Zappa"
    },
    {
        text: "A room without books is like a body without a soul.",
        author: "Marcus Tullius Cicero"
    },
    {
        text: "You only live once, but if you do it right, once is enough.",
        author: "Mae West"
    },
    {
        text: "Be the change that you wish to see in the world.",
        author: "Mahatma Gandhi"
    },
    {
        text: "In three words I can sum up everything I've learned about life: it goes on.",
        author: "Robert Frost"
    },
    {
        text: "If you want to know what a man's like, take a good look at how he treats his inferiors, not his equals.",
        author: "J.K. Rowling"
    },
    {
        text: "If you tell the truth, you don't have to remember anything.",
        author: "Mark Twain"
    },
    {
        text: "Friendship is the only cement that will ever hold the world together.",
        author: "Woodrow Wilson"
    },
    {
        text: "A friend is someone who knows all about you and still loves you.",
        author: "Elbert Hubbard"
    },
    {
        text: "To live is the rarest thing in the world. Most people just exist.",
        author: "Oscar Wilde"
    },
    {
        text: "Always forgive your enemies; nothing annoys them so much.",
        author: "Oscar Wilde"
    },
    {
        text: "Live as if you were to die tomorrow. Learn as if you were to live forever.",
        author: "Mahatma Gandhi"
    },
    {
        text: "Darkness cannot drive out darkness: only light can do that. Hate cannot drive out hate: only love can do that.",
        author: "Martin Luther King Jr."
    },
    {
        text: "Yesterday is history, tomorrow is a mystery, today is a gift of God, which is why we call it the present.",
        author: "Bill Keane"
    },
    {
        text: "It is better to be hated for what you are than to be loved for what you are not.",
        author: "André Gide"
    },
    {
        text: "I have not failed. I've just found 10,000 ways that won't work.",
        author: "Thomas A. Edison"
    },
    {
        text: "A woman is like a tea bag; you never know how strong it is until it's in hot water.",
        author: "Eleanor Roosevelt"
    },
    {
        text: "A day without sunshine is like, you know, night.",
        author: "Steve Martin"
    },
    {
        text: "The person, be it gentleman or lady, who has not pleasure in a good novel, must be intolerably stupid.",
        author: "Jane Austen"
    },
    {
        text: "Good friends, good books, and a sleepy conscience: this is the ideal life.",
        author: "Mark Twain"
    },
    {
        text: "Life is what happens to you while you're busy making other plans.",
        author: "John Lennon"
    },
    {
        text: "The future belongs to those who believe in the beauty of their dreams.",
        author: "Eleanor Roosevelt"
    },
    {
        text: "It is during our darkest moments that we must focus to see the light.",
        author: "Aristotle"
    }
];

// Predefined color palette for tags
const tagColors = [
    // Reds
    { name: 'Red', value: '#EF4444' },
    { name: 'Crimson', value: '#DC143C' },
    { name: 'Pink', value: '#EC4899' },
    { name: 'Coral', value: '#FF6B6B' },
    
    // Oranges & Yellows
    { name: 'Orange', value: '#FF8C42' },
    { name: 'Amber', value: '#FFA500' },
    { name: 'Yellow', value: '#FFD93D' },
    { name: 'Gold', value: '#FFD700' },
    
    // Greens
    { name: 'Lime', value: '#32CD32' },
    { name: 'Green', value: '#10B981' },
    { name: 'Forest', value: '#228B22' },
    { name: 'Teal', value: '#20B2AA' },
    
    // Blues
    { name: 'Cyan', value: '#00CED1' },
    { name: 'Blue', value: '#3B82F6' },
    { name: 'Navy', value: '#1E3A8A' },
    { name: 'Sky', value: '#87CEEB' },
    
    // Purples & Others
    { name: 'Purple', value: '#8B5CF6' },
    { name: 'Violet', value: '#9400D3' },
    { name: 'Brown', value: '#8B4513' },
    { name: 'Gray', value: '#6B7280' }
];

// Initialize dashboard
window.addEventListener('load', async function() {
    // Initialize theme system first
    initializeTheme();
    
    // Check authentication
    currentUser = await authUtils.checkAuthStatus();
    if (!currentUser) {
        window.location.href = '/login';
        return;
    }
    
    // Load saved user settings BEFORE loading data
    loadUserSettings();
    
    // Update welcome message
    document.getElementById('user-welcome').innerHTML = `
        Welcome, ${currentUser.username}
    `;
    
    // Load dashboard data
    await loadDashboardData();
    
    // Load user tags
    await loadUserTags();
    
    // Set daily motivational quote
    setDailyQuote();
    
    // Apply saved settings to UI elements (after everything is loaded)
    setTimeout(() => {
        applySettingsToUI();
    }, 100);
    
    // Setup event listeners
    setupEventListeners();
    
    // Setup filtering and sorting
    setupFiltersAndSorting();
});

// Load dashboard data
async function loadDashboardData() {
    try {
        authUtils.showLoadingSpinner();
        
        // Load goals and stats in parallel
        const [goalsResponse, statsResponse] = await Promise.all([
            fetch('/api/goals', { credentials: 'include' }),
            fetch('/api/dashboard/stats', { credentials: 'include' })
        ]);
        
        if (goalsResponse.ok) {
            goals = await goalsResponse.json();
            renderGoals();
        }
        
        if (statsResponse.ok) {
            const stats = await statsResponse.json();
            updateStatsDisplay(stats);
            updateProgressChart(stats);
        }
        
    } catch (error) {
        console.error('Error loading dashboard data:', error);
        authUtils.showErrorMessage('Failed to load dashboard data');
    } finally {
        authUtils.hideLoadingSpinner();
    }
}

// Load user tags
async function loadUserTags() {
    try {
        const response = await fetch('/api/tags', { credentials: 'include' });
        
        if (response.ok) {
            tags = await response.json();
            console.log('📊 Loaded user tags:', tags.length);
            
            // Populate tag filter dropdown
            populateTagFilterDropdown();
            // Populate tag filter bar
            populateTagFilterBar();
        } else {
            console.error('Failed to load tags');
        }
    } catch (error) {
        console.error('Error loading user tags:', error);
    }
}

// Update stats display
function updateStatsDisplay(stats) {
    // Stats display has been removed from the UI
    // Stats are now available via the Progress modal
    console.log('Dashboard stats:', stats);
}

// Update progress chart to show recent progress trends
function updateProgressChart(stats) {
    const ctx = document.getElementById('progress-chart');
    if (!ctx) {
        console.log('Progress chart canvas not found - will be initialized when modal opens');
        return;
    }
    
    const context = ctx.getContext('2d');
    
    if (progressChart) {
        progressChart.destroy();
    }
    
    // Generate recent progress data (last 7 days)
    const recentProgressData = generateRecentProgressData();
    
    // Handle case when there are no goals
    if (stats.total_goals === 0) {
        progressChart = new Chart(context, {
            type: 'line',
            data: {
                labels: ['No Data'],
                datasets: [{
                    label: 'Progress',
                    data: [0],
                    backgroundColor: 'rgba(229, 231, 235, 0.1)',
                    borderColor: '#E5E7EB',
                    borderWidth: 2,
                    fill: true
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        display: false
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        max: 100,
                        ticks: {
                            callback: function(value) {
                                return value + '%';
                            }
                        }
                    }
                }
            }
        });
        // Store the chart instance globally for modal access
        window.progressChart = progressChart;
        return;
    }
    
    progressChart = new Chart(context, {
        type: 'line',
        data: {
            labels: recentProgressData.labels,
            datasets: [{
                label: 'Subgoals Completed',
                data: recentProgressData.subgoalData,
                backgroundColor: 'rgba(59, 130, 246, 0.1)',
                borderColor: '#3B82F6',
                borderWidth: 3,
                fill: true,
                tension: 0.4,
                pointBackgroundColor: '#3B82F6',
                pointBorderColor: '#FFFFFF',
                pointBorderWidth: 2,
                pointRadius: 2,
                pointHoverRadius: 4
            }, {
                label: 'Goals Completed',
                data: recentProgressData.goalData,
                backgroundColor: 'rgba(16, 185, 129, 0.1)',
                borderColor: '#10B981',
                borderWidth: 3,
                fill: true,
                tension: 0.4,
                pointBackgroundColor: '#10B981',
                pointBorderColor: '#FFFFFF',
                pointBorderWidth: 2,
                pointRadius: 2,
                pointHoverRadius: 4
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            interaction: {
                intersect: false,
                mode: 'index'
            },
            plugins: {
                legend: {
                    display: false
                }
            },
            scales: {
                x: {
                    grid: {
                        display: false
                    },
                    ticks: {
                        color: '#6B7280',
                        font: {
                            size: 8
                        }
                    }
                },
                y: {
                    beginAtZero: true,
                    grid: {
                        color: 'rgba(229, 231, 235, 0.5)'
                    },
                    ticks: {
                        color: '#6B7280',
                        font: {
                            size: 8
                        }
                    }
                }
            }
        }
    });
    
    // Store the chart instance globally for modal access
    window.progressChart = progressChart;
}

// Generate recent progress data for the last 7 days
function generateRecentProgressData() {
    const days = [];
    const subgoalData = [];
    const goalData = [];
    
    // Get last 7 days (using local dates for consistency)
    for (let i = 6; i >= 0; i--) {
        const today = new Date();
        const date = new Date(today.getFullYear(), today.getMonth(), today.getDate() - i);
        
        // Format day label (e.g., "Mon", "Tue")
        const dayLabel = date.toLocaleDateString('en-US', { weekday: 'short' });
        days.push(dayLabel);
        
        // Calculate completed items for this day
        // For now, we'll use simulated data based on current progress
        // In a real app, you'd track this in the database
        const subgoalsCompleted = calculateDayProgress(date, 'subgoals');
        const goalsCompleted = calculateDayProgress(date, 'goals');
        
        subgoalData.push(subgoalsCompleted);
        goalData.push(goalsCompleted);
    }
    
    return {
        labels: days,
        subgoalData: subgoalData,
        goalData: goalData
    };
}

// Calculate progress for a specific day (simulated for now)
function calculateDayProgress(date, type) {
    // This is a simplified simulation based on current data
    // In a production app, you'd store completion timestamps in the database
    
    const today = new Date();
    const todayLocal = new Date(today.getFullYear(), today.getMonth(), today.getDate());
    const isToday = date.toDateString() === todayLocal.toDateString();
    const dayOfWeek = date.getDay();
    
    if (type === 'subgoals') {
        // Count recently completed subgoals
        let completedCount = 0;
        goals.forEach(goal => {
            if (goal.subgoals) {
                goal.subgoals.forEach(subgoal => {
                    if (subgoal.status === 'achieved') {
                        // Simulate that some were completed on different days
                        if (isToday || (dayOfWeek > 0 && Math.random() > 0.7)) {
                            completedCount++;
                        }
                    }
                });
            }
        });
        return completedCount;
    } else {
        // Count recently completed goals
        let completedCount = 0;
        goals.forEach(goal => {
            if (goal.status === 'completed') {
                // Simulate that some goals were completed on different days
                if (isToday || (dayOfWeek > 0 && Math.random() > 0.8)) {
                    completedCount++;
                }
            }
        });
        return completedCount;
    }
}

// Enhanced goal rendering with filtering and sorting
function renderGoals() {
    const container = document.getElementById('goals-container');
    
    // Filter and sort goals
    applyFiltersAndSort();
    
    // Check if no goals exist at all
    if (goals.length === 0) {
        container.innerHTML = `
            <div class="col-span-full flex flex-col items-center justify-center py-16 px-4">
                <div class="w-20 h-20 bg-gray-100 rounded-full flex items-center justify-center mb-6">
                    <i class="fas fa-target text-3xl text-gray-400"></i>
                </div>
                <h3 class="text-xl font-semibold text-gray-700 mb-2">No goals yet</h3>
                <p class="text-gray-500 mb-6 text-center max-w-md">Start your journey by creating your first goal. Break it down into manageable steps and track your progress.</p>
                <button onclick="showCreateGoalModal()" class="btn-primary px-6 py-3">
                    <i class="fas fa-plus mr-2"></i>
                    Create Your First Goal
                </button>
            </div>
        `;
        return;
    }
    
    // Check if filtered goals is empty
    if (filteredGoals.length === 0) {
        container.innerHTML = `
            <div class="col-span-full flex flex-col items-center justify-center py-12 px-4">
                <div class="w-16 h-16 bg-gray-100 rounded-full flex items-center justify-center mb-4">
                    <i class="fas fa-search text-2xl text-gray-400"></i>
                </div>
                <h3 class="text-lg font-medium text-gray-700 mb-2">No goals found</h3>
                <p class="text-gray-500 text-center">Try adjusting your filters or search terms.</p>
            </div>
        `;
        return;
    }
    
    // Apply view mode classes
    container.className = currentViewMode === 'grid' ? 'goals-grid' : 'goals-list';
    
    // Get goals for current page
    const startIndex = currentPage * goalsPerPage;
    const endIndex = startIndex + goalsPerPage;
    const goalsToShow = filteredGoals.slice(0, endIndex);
    
    // Render goals
    container.innerHTML = goalsToShow.map(goal => 
        currentViewMode === 'grid' ? renderGoalCardGrid(goal) : renderGoalCardList(goal)
    ).join('');
    
    // Add sticky hover functionality for grid view
    if (currentViewMode === 'grid') {
        setupStickyHover();
    }
    
    // Update load more button
    updateLoadMoreButton();
    
    // Compress description text to fit in goal cards
    compressDescriptionText();
}

// Helper function to check if mouse is below quick add input
function isMouseBelowQuickInput(mouseY, card) {
    const quickInput = card.querySelector('.quick-subgoal-input');
    if (!quickInput) {
        // If no quick input (completed goals), allow expansion anywhere
        return true;
    }
    
    const inputRect = quickInput.getBoundingClientRect();
    const inputBottom = inputRect.bottom;
    
    return mouseY > inputBottom;
}

// Setup smooth professional hover functionality
function setupStickyHover() {
    const goalCards = document.querySelectorAll('.goal-card-grid');
    
    goalCards.forEach(card => {
        const goalId = card.getAttribute('data-goal-id');
        let isExpanded = false;
        let animationFrame = null;
        let expandTimeout = null;
        let collapseTimeout = null;
        let lastMouseY = 0;
        let isInteracting = false;
        
        // Cache DOM queries for performance
        const quickInput = card.querySelector('.quick-subgoal-input');
        const inputBottom = quickInput ? quickInput.getBoundingClientRect().bottom : 0;
        
        // Restore sticky state if it was active before re-render
        if (stickyHoverStates.get(goalId)) {
            card.classList.add('sticky-hover');
            isExpanded = true;
        }
        
        // Ultra-smooth 3-frame expansion per subgoal
        const expandCard = () => {
            if (isExpanded) return;
            
            clearTimeout(collapseTimeout);
            clearTimeout(expandTimeout);
            
            // Start card elevation immediately
            card.classList.add('sticky-hover');
            stickyHoverStates.set(goalId, true);
            isExpanded = true;
            
            // Check if we need to dynamically create hidden subgoals
            let hiddenSubgoals = card.querySelectorAll('.hidden-subgoal');
            
            if (hiddenSubgoals.length === 0) {
                // Need to create hidden subgoals from stored data
                const hiddenDataElement = card.querySelector('.hidden-subgoals-data');
                if (hiddenDataElement) {
                    const hiddenSubgoalsData = JSON.parse(hiddenDataElement.getAttribute('data-hidden-subgoals'));
                    const subgoalsList = card.querySelector('.subgoals-list');
                    const hoverHint = card.querySelector('.hover-hint-item');
                    
                    // Create and insert hidden subgoals before the hover hint
                    hiddenSubgoalsData.forEach((subgoal, index) => {
                        const subgoalElement = document.createElement('div');
                        subgoalElement.className = `subgoal-item ${subgoal.status === 'achieved' ? 'completed' : ''} hidden-subgoal`;
                        subgoalElement.style.setProperty('--animation-delay', `${(index + 3) * 0.05}s`);
                        subgoalElement.innerHTML = `
                            <div class="flex items-center w-full py-0.25">
                                <input type="checkbox" 
                                       id="subgoal-${subgoal.id}"
                                       class="h-3 w-3 text-blue-600 rounded mr-2 flex-shrink-0" 
                                       ${subgoal.status === 'achieved' ? 'checked' : ''}
                                       onclick="event.stopPropagation();"
                                       onchange="quickUpdateSubgoal(${subgoal.id}, this.checked, ${goalId}); event.stopPropagation();">
                                <span class="truncate flex-1 cursor-pointer text-sm" 
                                      onclick="event.stopPropagation(); toggleSubgoalCheckbox(${subgoal.id}, ${goalId});">${subgoal.title}</span>
                                ${formatDaysLeft(subgoal.target_date, subgoal.status)}
                            </div>`;
                        
                        // Insert before hover hint
                        subgoalsList.insertBefore(subgoalElement, hoverHint);
                    });
                    
                    // Update the hidden subgoals query
                    hiddenSubgoals = card.querySelectorAll('.hidden-subgoal');
                }
            }
            
            // 3-frame expansion: 0% → 33% → 66% → 100% height
            hiddenSubgoals.forEach((subgoal, index) => {
                const baseDelay = index * 30; // 30ms between each subgoal start
                
                // Frame 1: 33% height
                setTimeout(() => {
                    subgoal.classList.add('reveal-frame-1');
                }, baseDelay);
                
                // Frame 2: 66% height  
                setTimeout(() => {
                    subgoal.classList.remove('reveal-frame-1');
                    subgoal.classList.add('reveal-frame-2');
                }, baseDelay + 30); // 30ms between frames
                
                // Frame 3: 100% height
                setTimeout(() => {
                    subgoal.classList.remove('reveal-frame-2');
                    subgoal.classList.add('reveal-step');
                }, baseDelay + 60); // 30ms between frames
            });
        };
        
        // Ultra-smooth 3-frame collapse per subgoal (reverse order)
        const collapseCard = () => {
            if (!isExpanded || isInteracting) return;
            
            clearTimeout(expandTimeout);
            clearTimeout(collapseTimeout);
            
            card.classList.add('hover-exit');
            
            // Get all revealed subgoals for 3-frame collapse
            const revealedSubgoals = card.querySelectorAll('.hidden-subgoal.reveal-step');
            const reversedSubgoals = Array.from(revealedSubgoals).reverse();
            
            // 3-frame collapse: 100% → 66% → 33% → 0% height
            reversedSubgoals.forEach((subgoal, index) => {
                const baseDelay = index * 25; // 25ms between each subgoal start
                
                // Frame 1: 66% height
                setTimeout(() => {
                    subgoal.classList.remove('reveal-step');
                    subgoal.classList.add('collapse-frame-1');
                }, baseDelay);
                
                // Frame 2: 33% height
                setTimeout(() => {
                    subgoal.classList.remove('collapse-frame-1');
                    subgoal.classList.add('collapse-frame-2');
                }, baseDelay + 25); // 25ms between frames
                
                // Frame 3: 0% height (fully hidden) - then remove from DOM
                setTimeout(() => {
                    subgoal.classList.remove('collapse-frame-2');
                    // Remove from DOM immediately after collapse animation completes
                    subgoal.remove();
                }, baseDelay + 50); // 25ms between frames
            });
            
            // Remove card classes after all subgoals are fully collapsed
            const totalCollapseTime = reversedSubgoals.length * 100 + 75;
            setTimeout(() => {
                card.classList.remove('sticky-hover', 'hover-exit');
                stickyHoverStates.set(goalId, false);
                isExpanded = false;
                // Individual subgoals remove themselves during collapse animation
            }, totalCollapseTime);
        };
        
        // Debounced position check with RAF
        const checkMousePosition = (mouseY) => {
            // Cancel pending animation frame
            if (animationFrame) {
                cancelAnimationFrame(animationFrame);
            }
            
            animationFrame = requestAnimationFrame(() => {
                const shouldExpand = isMouseBelowQuickInput(mouseY, card);
                
                if (shouldExpand && !isExpanded && !isInteracting) {
                    expandTimeout = setTimeout(expandCard, 50); // Small delay for stability
                } else if (!shouldExpand && isExpanded && !isInteracting) {
                    collapseTimeout = setTimeout(collapseCard, 200); // Longer delay before starting collapse
                }
            });
        };
        
        // Optimized mouse tracking
        let mouseMoveThrottle = null;
        card.addEventListener('mousemove', function(event) {
            // Throttle mousemove to 60fps
            if (!mouseMoveThrottle) {
                mouseMoveThrottle = setTimeout(() => {
                    mouseMoveThrottle = null;
                    lastMouseY = event.clientY;
                    checkMousePosition(event.clientY);
                }, 16); // ~60fps
            }
        });
        
        // Clean animation on mouse leave
        card.addEventListener('mouseleave', function() {
            clearTimeout(expandTimeout);
            if (!isInteracting) {
                collapseTimeout = setTimeout(collapseCard, 250); // Generous delay before collapse
            }
        });
        
        // Handle interactions
        const startInteraction = () => {
            isInteracting = true;
            expandCard();
        };
        
        const endInteraction = () => {
            isInteracting = false;
            // Check if we should collapse
            setTimeout(() => {
                if (!card.matches(':hover') && !isInteracting) {
                    collapseCard();
                }
            }, 300);
        };
        
        // Checkbox interactions
        const checkboxes = card.querySelectorAll('input[type="checkbox"]');
        checkboxes.forEach(checkbox => {
            checkbox.addEventListener('change', startInteraction);
            checkbox.addEventListener('blur', endInteraction);
        });
        
        // Subgoal text clicks
        const subgoalTexts = card.querySelectorAll('.subgoal-item span.cursor-pointer');
        subgoalTexts.forEach(text => {
            text.addEventListener('click', () => {
                startInteraction();
                // Auto end after interaction
                setTimeout(endInteraction, 500);
            });
        });
        
        // Quick input interactions
        if (quickInput) {
            quickInput.addEventListener('focus', startInteraction);
            quickInput.addEventListener('blur', endInteraction);
        }
    });
}

// Render goal card for grid view
function renderGoalCardGrid(goal) {
    // Enhanced progress colors with gradients
    const progressColor = goal.progress >= 100 ? '#10b981' : 
                         goal.progress >= 75 ? '#3b82f6' : 
                         goal.progress >= 25 ? '#f59e0b' : '#ef4444';
    
    // Improved circle calculations for cleaner appearance
    const radius = 26;
    const circumference = 2 * Math.PI * radius;
    const strokeDashoffset = circumference - (goal.progress / 100) * circumference;
    
    const hasHiddenSubgoals = goal.subgoals.length > 3;
    
    return `
        <div class="goal-card-grid expandable-goal-card" 
             data-goal-id="${goal.id}">
            
            <!-- Modern Header with Integrated Status -->
            <div class="card-header-section">
                <div class="flex items-start justify-between gap-3 mb-2">
                    <div class="flex items-center gap-2 flex-1 min-w-0">
                        <div class="status-dot ${getStatusDotClass(goal.status)}" 
                             title="${goal.status.replace('_', ' ').toUpperCase()}"></div>
                        <h3 class="goal-title-modern">${goal.title}</h3>
                    </div>
                    <div class="card-menu-container">
                        <button class="card-menu-btn" onclick="toggleCardMenu(${goal.id}); event.stopPropagation();" title="More options">
                            <i class="fas fa-ellipsis-h"></i>
                        </button>
                        <div id="card-menu-${goal.id}" class="card-dropdown-menu hidden" style="border: 1px solid #cbd5e1 !important;">
                            <button onclick="editGoal(${goal.id}); closeCardMenu(${goal.id}); event.stopPropagation();" class="card-menu-item">
                                <i class="fas fa-edit"></i>
                                <span>Edit</span>
                            </button>
                            ${goal.status !== 'completed' ? `
                                <button onclick="updateGoalStatus(${goal.id}, 'completed'); closeCardMenu(${goal.id}); event.stopPropagation();" class="card-menu-item">
                                    <i class="fas fa-trophy"></i>
                                    <span>Complete</span>
                                </button>
                            ` : `
                                <button onclick="updateGoalStatus(${goal.id}, 'working'); closeCardMenu(${goal.id}); event.stopPropagation();" class="card-menu-item">
                                    <i class="fas fa-undo"></i>
                                    <span>Incomplete</span>
                                </button>
                            `}
                            <div class="card-menu-divider"></div>
                            <button onclick="deleteGoal(${goal.id}); closeCardMenu(${goal.id}); event.stopPropagation();" class="card-menu-item card-menu-danger">
                                <i class="fas fa-trash"></i>
                                <span>Delete</span>
                            </button>
                        </div>
                    </div>
                </div>
                
                <!-- Tags Row -->
                ${goal.tags && goal.tags.length > 0 ? `
                    <div class="tags-container mb-3">
                        ${renderModernTagBadges(goal, 3)}
                    </div>
                ` : ''}
                
                <!-- Description with consistent 1-line spacing -->
                <div class="${goal.description ? 'description-container' : 'description-placeholder'}">
                    ${goal.description ? `
                        <p class="goal-description-modern" id="desc-${goal.id}">${goal.description}</p>
                    ` : ''}
                </div>
                
                <!-- Enhanced Progress and Date Section -->
                <div class="mt-4 mb-4 p-3 progress-stats-section rounded-lg">
                    <div class="flex items-center justify-between">
                        <!-- Progress Section -->
                        <div class="flex items-center gap-4">
                            <!-- Larger Progress Circle -->
                            <div class="relative w-12 h-12">
                                <svg class="w-12 h-12 transform -rotate-90" viewBox="0 0 48 48">
                                    <circle cx="24" cy="24" r="20" stroke="#e5e7eb" stroke-width="4" fill="none"/>
                                    <circle cx="24" cy="24" r="20" 
                                            stroke="${goal.progress >= 100 ? '#10b981' : goal.progress >= 75 ? '#3b82f6' : goal.progress >= 25 ? '#f59e0b' : '#ef4444'}" 
                                            stroke-width="4" 
                                            fill="none"
                                            stroke-dasharray="${2 * Math.PI * 20}"
                                            stroke-dashoffset="${2 * Math.PI * 20 * (1 - goal.progress / 100)}"
                                            stroke-linecap="round"/>
                                </svg>
                                <div class="absolute inset-0 flex items-center justify-center">
                                    <span class="text-sm font-normal text-gray-800">${Math.round(goal.progress)}%</span>
                                </div>
                            </div>
                            <!-- Progress Details -->
                            <div class="flex flex-col gap-1">
                                <span class="text-xs font-medium text-gray-700">
                                    ${goal.subgoals.filter(sg => sg.status === 'achieved').length} of ${goal.subgoals.length} completed
                                </span>
                                <div class="w-24 h-2 bg-gray-200 rounded-full">
                                    <div class="h-2 rounded-full transition-all duration-300" 
                                         style="width: ${goal.progress}%; background-color: ${goal.progress >= 100 ? '#10b981' : goal.progress >= 75 ? '#3b82f6' : goal.progress >= 25 ? '#f59e0b' : '#ef4444'}"></div>
                                </div>
                            </div>
                        </div>
                        
                        <!-- Target Date Section -->
                        ${goal.target_date ? `
                            <div class="text-right">
                                <div class="text-xs font-medium text-gray-600 mb-1">Target Date</div>
                                <div class="text-sm font-bold text-gray-800 mb-1">${new Date(goal.target_date).toLocaleDateString('en-US', {month: 'short', day: 'numeric'})}</div>
                                <div class="inline-block">
                                    ${formatDaysLeft(goal.target_date, goal.status)}
                                </div>
                            </div>
                        ` : ''}
                    </div>
                </div>
            </div>
            
            <!-- Flexible content area -->
            <div class="flex flex-col flex-1 mt-4">
                <!-- Quick Add Subgoal Input - now in consistent position -->
                ${goal.status !== 'completed' ? `
                    <div class="mt-6 mb-4 px-1">
                        <input type="text" 
                               id="quick-subgoal-${goal.id}"
                               class="quick-subgoal-input w-full text-xs px-2 py-1.5 border border-gray-200 rounded-md focus:border-blue-400 focus:ring-1 focus:ring-blue-400 focus:outline-none transition-all duration-200"
                               placeholder="Add quick sub-goal..." 
                               onkeypress="handleQuickSubgoalKeypress(event, ${goal.id})"
                               onclick="event.stopPropagation();"
                               onfocus="event.stopPropagation(); maintainStickyHover(${goal.id})"
                               onblur="event.stopPropagation();">
                    </div>
                ` : ''}
                
                <!-- Subgoals Preview with Pure CSS Hover Expansion -->
                ${goal.subgoals.length > 0 ? `
                    <div class="border-t pt-1.5 mt-auto subgoals-section ${hasHiddenSubgoals ? 'has-hidden-subgoals' : ''}">
                        <div class="flex items-center justify-between mb-0.5">
                            <span class="text-sm text-gray-600">Sub-goals</span>
                            <span class="text-xs bg-blue-100 text-blue-800 px-1.5 py-0.5 rounded-full">
                                ${goal.subgoals.filter(sg => sg.status === 'achieved').length}/${goal.subgoals.length}
                            </span>
                        </div>
                        
                        <!-- Single Unified Subgoals List -->
                        <div class="subgoals-list space-y-0">
                            ${(() => {
                                const sortedSubgoals = sortSubgoalsForDisplay(goal.subgoals);
                                const visibleSlots = 3;
                                let output = '';
                                
                                // Only render visible subgoals initially (first 3)
                                sortedSubgoals.slice(0, visibleSlots).forEach((subgoal, index) => {
                                    output += `
                                        <div class="subgoal-item ${subgoal.status === 'achieved' ? 'completed' : ''} visible-subgoal" 
                                             style="--animation-delay: ${index * 0.05}s">
                                            <div class="flex items-center w-full py-0.25">
                                                <input type="checkbox" 
                                                       id="subgoal-${subgoal.id}"
                                                       class="h-3 w-3 text-blue-600 rounded mr-2 flex-shrink-0" 
                                                       ${subgoal.status === 'achieved' ? 'checked' : ''}
                                                       onclick="event.stopPropagation();"
                                                       onchange="quickUpdateSubgoal(${subgoal.id}, this.checked, ${goal.id}); event.stopPropagation();">
                                                <span class="truncate flex-1 cursor-pointer text-sm" 
                                                      onclick="event.stopPropagation(); toggleSubgoalCheckbox(${subgoal.id}, ${goal.id});">${subgoal.title}</span>
                                                ${formatDaysLeft(subgoal.target_date, subgoal.status)}
                                            </div>
                                        </div>`;
                                });
                                
                                // Store hidden subgoals data for later expansion (if any exist)
                                if (sortedSubgoals.length > visibleSlots) {
                                    const hiddenSubgoals = sortedSubgoals.slice(visibleSlots);
                                    // Add hidden subgoals as data attribute for expansion logic
                                    output += `<div class="hidden-subgoals-data" style="display: none;" data-hidden-subgoals='${JSON.stringify(hiddenSubgoals)}'></div>`;
                                }
                                
                                // Add empty spacer divs to ensure consistent height for cards with fewer subgoals
                                const visibleCount = Math.min(sortedSubgoals.length, visibleSlots);
                                for (let i = visibleCount; i < visibleSlots; i++) {
                                    output += `<div class="subgoal-item visible-subgoal spacer-item">
                                        <div class="flex items-center w-full py-0.25" style="height: 1.5rem;">
                                            <!-- Empty spacer to maintain consistent card height -->
                                        </div>
                                    </div>`;
                                }
                                
                                return output;
                            })()}
                            
                            ${hasHiddenSubgoals ? `
                                <div class="hover-hint-item text-xs text-gray-400 mt-1">
                                    <i class="fas fa-chevron-down mr-1"></i>
                                    <span class="hint-text">+${goal.subgoals.length - 3} more (hover to expand)</span>
                                </div>
                            ` : `
                                <div class="hover-hint-item text-xs text-gray-400 mt-1" style="opacity: 0; height: 1rem;">
                                    <!-- Invisible spacer to maintain consistent spacing -->
                                </div>
                            `}
                        </div>
                    </div>
                ` : `
                    <div class="border-t pt-1.5 mt-auto subgoals-section">
                        <!-- Reserve space for consistent card height -->
                        <div class="subgoals-list space-y-0">
                            <!-- Add 3 empty spacer slots for consistent height -->
                            ${Array.from({length: 3}, (_, i) => `
                                <div class="subgoal-item visible-subgoal spacer-item">
                                    <div class="flex items-center w-full py-0.25" style="height: 1.5rem;">
                                        <!-- Empty spacer slot ${i + 1} -->
                                    </div>
                                </div>
                            `).join('')}
                            
                            <!-- Always show invisible spacer hint for consistent spacing -->
                            <div class="hover-hint-item text-xs text-gray-400 mt-1" style="opacity: 0; height: 1rem;">
                                <!-- Invisible spacer for consistent spacing -->
                            </div>
                        </div>
                        
                        <!-- "No sub-goals yet" message positioned over the spacers -->
                        <div class="absolute inset-0 flex items-center justify-center">
                            <span class="text-sm text-gray-500">No sub-goals yet</span>
                        </div>
                    </div>
                `}
            </div>
            
        </div>
    `;
}

// Simple CSS-based text compression - no JavaScript needed
function compressDescriptionText() {
    // CSS handles this automatically with text-overflow: ellipsis
    // No JavaScript compression needed - rely on CSS overflow handling
}

// Render goal card for list view
function renderGoalCardList(goal) {
    return `
        <div class="modern-goal-card p-6 hover:border-gray-300 transition-all">
            <div class="flex items-start justify-between">
                <div class="flex-1">
                    <div class="flex items-center space-x-3 mb-2">
                        <h3 class="text-xl font-semibold text-gray-900">${goal.title}</h3>
                        <span class="status-badge ${getStatusBadgeClass(goal.status)}" 
                              title="${goal.status.replace('_', ' ').toUpperCase()}">
                            <i class="fas ${getStatusIcon(goal.status)}"></i>
                        </span>
                    </div>
                    
                    <!-- Tags -->
                    ${goal.tags && goal.tags.length > 0 ? `
                        <div class="flex flex-wrap gap-1 mb-3">
                            ${renderTagBadges(goal, 5)}
                        </div>
                    ` : ''}
                    
                    ${goal.description ? `<p class="text-gray-600 mb-4">${goal.description}</p>` : ''}
                    
                    <div class="flex items-center space-x-6 text-sm text-gray-500 mb-4">
                        <span class="flex items-center">
                            <i class="fas fa-calendar-alt mr-2"></i>
                            ${goal.target_date ? parseLocalDate(goal.target_date).toLocaleDateString() : 'No target date'}
                        </span>
                        <span class="flex items-center">
                            <i class="fas fa-tasks mr-2"></i>
                            ${goal.subgoals.filter(sg => sg.status === 'achieved').length}/${goal.subgoals.length} sub-goals
                        </span>
                        <span class="flex items-center">
                            <i class="fas fa-chart-pie mr-2"></i>
                            ${goal.progress}% complete
                        </span>
                    </div>
                    
                    <!-- Progress Bar -->
                    <div class="w-full bg-gray-200 rounded-full h-2 mb-4">
                        <div class="progress-bar h-2 rounded-full transition-all duration-700" 
                             style="width: ${goal.progress}%"></div>
                    </div>
                    
                    <!-- Subgoals -->
                    ${goal.subgoals.length > 0 ? `
                        <div class="grid grid-cols-1 md:grid-cols-2 gap-2">
                            ${sortSubgoalsForDisplay(goal.subgoals).map(subgoal => `
                                <div class="flex items-center p-2 rounded hover:bg-gray-50">
                                    <input type="checkbox" 
                                           id="subgoal-list-${subgoal.id}"
                                           class="h-4 w-4 text-blue-600 rounded mr-3" 
                                           ${subgoal.status === 'achieved' ? 'checked' : ''}
                                           onchange="quickUpdateSubgoal(${subgoal.id}, this.checked, ${goal.id})">
                                    <span class="text-sm cursor-pointer ${subgoal.status === 'achieved' ? 'line-through text-gray-500' : 'text-gray-700'}"
                                          onclick="toggleSubgoalCheckboxList(${subgoal.id}, ${goal.id})">${subgoal.title}</span>
                                </div>
                            `).join('')}
                        </div>
                    ` : ''}
                </div>
                
                <div class="flex flex-col space-y-2 ml-6">
                    ${goal.status !== 'completed' ? `
                        <button onclick="updateGoalStatus(${goal.id}, 'completed')" class="btn-success text-sm px-4 py-2">
                            <i class="fas fa-trophy mr-1"></i>
                            Complete
                        </button>
                    ` : ''}
                    <button onclick="editGoal(${goal.id})" class="btn-secondary text-sm px-4 py-2">
                        <i class="fas fa-edit mr-1"></i>
                        Edit
                    </button>
                    <button onclick="deleteGoal(${goal.id})" class="text-red-500 hover:text-red-700 text-sm px-4 py-2 hover:bg-red-50 rounded-lg transition-colors">
                        <i class="fas fa-trash mr-1"></i>
                        Delete
                    </button>
                </div>
            </div>
        </div>
    `;
}

// Helper function to calculate days until deadline
function getDaysUntilDeadline(targetDate) {
    if (!targetDate) return null;
    
    const target = parseLocalDate(targetDate);
    // Use local date for today to match parseLocalDate behavior
    const today = new Date();
    const todayLocal = new Date(today.getFullYear(), today.getMonth(), today.getDate());
    const diffTime = target - todayLocal;
    const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24));
    
    return diffDays;
}

// Helper function to sort subgoals with completed ones at the bottom
function sortSubgoalsForDisplay(subgoals) {
    return subgoals.slice().sort((a, b) => {
        // Completed subgoals go to bottom
        if (a.status === 'achieved' && b.status !== 'achieved') return 1;
        if (a.status !== 'achieved' && b.status === 'achieved') return -1;
        // Among same status, maintain original order (by order_index if available)
        return (a.order_index || 0) - (b.order_index || 0);
    });
}

// Helper function to format days left indicator
function formatDaysLeft(targetDate, status) {
    if (!targetDate || status === 'achieved') return '';
    
    const daysLeft = getDaysUntilDeadline(targetDate);
    
    if (daysLeft === null) return '';
    
    let colorClass = '';
    let text = '';
    
    if (daysLeft < 0) {
        colorClass = 'text-red-500 bg-red-50';
        text = `${Math.abs(daysLeft)}d overdue`;
    } else if (daysLeft === 0) {
        colorClass = 'text-orange-600 bg-orange-50';
        text = 'Due today';
    } else if (daysLeft === 1) {
        colorClass = 'text-orange-600 bg-orange-50';
        text = 'Due tomorrow';
    } else if (daysLeft <= 3) {
        colorClass = 'text-orange-600 bg-orange-50';
        text = `${daysLeft}d left`;
    } else if (daysLeft <= 7) {
        colorClass = 'text-yellow-600 bg-yellow-50';
        text = `${daysLeft}d left`;
    } else {
        colorClass = 'text-gray-500 bg-gray-50';
        text = `${daysLeft}d left`;
    }
    
    return `<span class="text-xs px-2 py-1 rounded-full ${colorClass} ml-auto flex-shrink-0">${text}</span>`;
}

// Helper functions for goal status
function getStatusColor(status) {
    switch (status) {
        case 'completed': return 'text-green-600';
        case 'working': return 'text-amber-600';
        case 'started': return 'text-blue-600';
        case 'created': return 'text-gray-600';
        default: return 'text-gray-600';
    }
}

function getStatusIcon(status) {
    switch (status) {
        case 'completed': return 'fa-trophy';
        case 'working': return 'fa-rocket';
        case 'started': return 'fa-play';
        case 'created': return 'fa-clock';
        default: return 'fa-circle';
    }
}

function getStatusBadgeClass(status) {
    switch (status) {
        case 'completed': return 'status-completed';
        case 'working': return 'status-working';
        case 'started': return 'status-started';
        case 'created': return 'status-created';
        default: return 'status-created';
    }
}

// Modern status dot classes for redesigned header
function getStatusDotClass(status) {
    switch (status) {
        case 'completed': return 'status-dot-completed';
        case 'working': return 'status-dot-working';
        case 'started': return 'status-dot-started';
        case 'created': return 'status-dot-created';
        default: return 'status-dot-created';
    }
}

// Calculate days remaining until target date
function calculateDaysRemaining(targetDate) {
    if (!targetDate) return '';
    
    const today = new Date();
    const target = parseLocalDate(targetDate);
    const diffTime = target - today;
    const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24));
    
    if (diffDays < 0) {
        return `<span class="days-overdue">${Math.abs(diffDays)} days overdue</span>`;
    } else if (diffDays === 0) {
        return `<span class="days-today">Due today</span>`;
    } else if (diffDays === 1) {
        return `<span class="days-upcoming">Due tomorrow</span>`;
    } else if (diffDays <= 7) {
        return `<span class="days-upcoming">${diffDays} days left</span>`;
    } else {
        return `<span class="days-future">${diffDays} days left</span>`;
    }
}

function calculateDaysRemainingCompact(targetDate) {
    if (!targetDate) return '';
    
    const today = new Date();
    const target = parseLocalDate(targetDate);
    const diffTime = target - today;
    const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24));
    
    if (diffDays < 0) {
        return `${Math.abs(diffDays)}d overdue`;
    } else if (diffDays === 0) {
        return `Due today`;
    } else if (diffDays === 1) {
        return `Due tomorrow`;
    } else if (diffDays <= 7) {
        return `${diffDays} days left`;
    } else {
        return `${diffDays} days left`;
    }
}

function getDaysRemainingClass(targetDate) {
    if (!targetDate) return '';
    
    const today = new Date();
    const target = parseLocalDate(targetDate);
    const diffTime = target - today;
    const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24));
    
    if (diffDays < 0) {
        return 'days-overdue';
    } else if (diffDays === 0) {
        return 'days-today';
    } else if (diffDays <= 7) {
        return 'days-upcoming';
    } else {
        return 'days-future';
    }
}

// Card dropdown menu functions
window.toggleCardMenu = function(goalId) {
    const menu = document.getElementById(`card-menu-${goalId}`);
    const isVisible = !menu.classList.contains('hidden');
    
    // Close all other card menus first
    document.querySelectorAll('.card-dropdown-menu').forEach(m => {
        if (m.id !== `card-menu-${goalId}`) {
            m.classList.add('hidden');
        }
    });
    
    if (isVisible) {
        menu.classList.add('hidden');
    } else {
        menu.classList.remove('hidden');
    }
}

window.closeCardMenu = function(goalId) {
    const menu = document.getElementById(`card-menu-${goalId}`);
    if (menu) {
        menu.classList.add('hidden');
    }
}

// Close all card menus when clicking outside
document.addEventListener('click', function(event) {
    if (!event.target.closest('.card-menu-container')) {
        document.querySelectorAll('.card-dropdown-menu').forEach(menu => {
            menu.classList.add('hidden');
        });
    }
});

// Set daily motivational quote
function setDailyQuote() {
    // Calculate days since epoch to ensure daily rotation through all quotes
    const today = new Date();
    const daysSinceEpoch = Math.floor(today.getTime() / (1000 * 60 * 60 * 24));
    const quoteIndex = daysSinceEpoch % motivationalQuotes.length;
    const quote = motivationalQuotes[quoteIndex];
    document.getElementById('daily-quote').innerHTML = quote.text;
    document.getElementById('quote-author').innerHTML = `— ${quote.author}`;
}

// Modal functions - make globally accessible
window.showCreateGoalModal = function() {
    console.log('🎯 Opening create goal modal'); // Debug log
    document.getElementById('create-goal-modal').classList.remove('hidden');
    // Set default target date to 30 days from now (using local time to avoid timezone shifts)
    const defaultDate = new Date();
    defaultDate.setDate(defaultDate.getDate() + 30);
    // Format as YYYY-MM-DD without timezone conversion
    const year = defaultDate.getFullYear();
    const month = String(defaultDate.getMonth() + 1).padStart(2, '0');
    const day = String(defaultDate.getDate()).padStart(2, '0');
    document.getElementById('goal-target-date').value = `${year}-${month}-${day}`;
    
    // Initialize tag selector
    selectedTagIds = [];
    renderTagSelector('create-goal-tags-grid', selectedTagIds);
    
    // Auto-focus on the goal title input field
    setTimeout(() => {
        const goalTitleInput = document.getElementById('goal-title');
        if (goalTitleInput) {
            goalTitleInput.focus();
        }
    }, 100);
    
    // Add ESC key listener to close create modal
    const handleCreateModalEsc = function(e) {
        if (e.key === 'Escape' || e.keyCode === 27) {
            const createModal = document.getElementById('create-goal-modal');
            // Only close if the create modal is visible (not hidden)
            if (createModal && !createModal.classList.contains('hidden')) {
                console.log('🎯 ESC key pressed - closing create modal'); // Debug log
                closeCreateGoalModal();
            }
        }
    };
    
    // Remove any existing ESC listeners and add new one
    document.removeEventListener('keydown', window.createModalEscHandler);
    window.createModalEscHandler = handleCreateModalEsc;
    document.addEventListener('keydown', handleCreateModalEsc);
    
    console.log('⌨️ ESC key listener attached to create modal'); // Debug log
}

window.closeCreateGoalModal = function() {
    console.log('🎯 Closing create goal modal'); // Debug log
    
    // Remove ESC key listener when closing modal
    if (window.createModalEscHandler) {
        document.removeEventListener('keydown', window.createModalEscHandler);
        window.createModalEscHandler = null;
        console.log('⌨️ ESC key listener removed from create modal'); // Debug log
    }
    
    document.getElementById('create-goal-modal').classList.add('hidden');
    document.getElementById('create-goal-form').reset();
    
    // Clear tag selection
    selectedTagIds = [];
}

// Goal management functions
async function createGoal(goalData) {
    try {
        const response = await fetch('/api/goals', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(goalData),
            credentials: 'include'
        });
        
        if (response.ok) {
            const newGoal = await response.json();
            
            // Set tags if any are selected
            if (selectedTagIds.length > 0) {
                const tagResponse = await fetch(`/api/goals/${newGoal.id}/tags`, {
                    method: 'PUT',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({ tag_ids: selectedTagIds }),
                    credentials: 'include'
                });
                
                if (!tagResponse.ok) {
                    console.warn('Failed to set goal tags, but goal was created successfully');
                }
            }
            
            if (window.authUtils) {
                window.authUtils.showSuccessMessage(`Goal "${newGoal.title}" created successfully`);
            }
            await loadDashboardData();
            closeCreateGoalModal();
        } else {
            const error = await response.json();
            if (window.authUtils) {
                window.authUtils.showErrorMessage(error.error || 'Failed to create goal');
            }
        }
    } catch (error) {
        console.error('Error creating goal:', error);
        if (window.authUtils) {
            window.authUtils.showErrorMessage('Connection error. Please try again');
        }
    }
}

async function updateGoalStatus(goalId, status) {
    try {
        const response = await fetch(`/api/goals/${goalId}`, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ status }),
            credentials: 'include'
        });
        
        if (response.ok) {
            const updatedGoal = await response.json();
            if (status === 'completed') {
                authUtils.showSuccessMessage(`Congratulations! Goal "${updatedGoal.title}" completed!`);
                // Add celebration effect
                createCelebrationEffect();
            } else {
                authUtils.showSuccessMessage('Goal updated successfully');
            }
            await loadDashboardData();
        } else {
            const error = await response.json();
            authUtils.showErrorMessage(error.error || 'Failed to update goal');
        }
    } catch (error) {
        console.error('Error updating goal:', error);
        authUtils.showErrorMessage('Connection error. Please try again');
    }
}

async function deleteGoal(goalId) {
    if (!confirm('Are you sure you want to delete this goal? This action cannot be undone.')) {
        return;
    }
    
    try {
        const response = await fetch(`/api/goals/${goalId}`, {
            method: 'DELETE',
            credentials: 'include'
        });
        
        if (response.ok) {
            authUtils.showSuccessMessage('Goal deleted successfully');
            await loadDashboardData();
        } else {
            const error = await response.json();
            authUtils.showErrorMessage(error.error || 'Failed to delete goal');
        }
    } catch (error) {
        console.error('Error deleting goal:', error);
        authUtils.showErrorMessage('Connection error. Please try again');
    }
}

// Subtle celebration effect
function createCelebrationEffect() {
    // Just add a subtle visual feedback instead of confetti
    const dashboard = document.querySelector('.container');
    if (dashboard) {
        dashboard.style.transform = 'scale(1.01)';
        dashboard.style.transition = 'transform 0.2s ease';
        
        setTimeout(() => {
            dashboard.style.transform = 'scale(1)';
            setTimeout(() => {
                dashboard.style.transform = '';
                dashboard.style.transition = '';
            }, 200);
        }, 200);
    }
}

// Quick action functions - make globally accessible
window.viewHistory = async function() {
    console.log('🎯 Opening history view'); // Debug log
    try {
        const response = await fetch('/api/reports/history', { credentials: 'include' });
        
        if (response.ok) {
            const historyData = await response.json();
            showHistoryModal(historyData);
        } else {
            authUtils.showErrorMessage('Failed to load history');
        }
    } catch (error) {
        console.error('Error loading history:', error);
        authUtils.showErrorMessage('Connection error. Please try again');
    }
}

window.generateReport = function() {
    const totalGoals = goals.length;
    const completedGoals = goals.filter(g => g.status === 'completed').length;
    const workingGoals = goals.filter(g => g.status === 'working').length;
    const startedGoals = goals.filter(g => g.status === 'started').length;
    const activeGoals = workingGoals + startedGoals;
    const avgProgress = totalGoals > 0 ? Math.round(goals.reduce((sum, g) => sum + g.progress, 0) / totalGoals) : 0;
    
    const modal = document.createElement('div');
    modal.className = 'fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50';
    modal.innerHTML = `
        <div class="modern-card p-8 rounded-xl shadow-2xl max-w-md w-full mx-4">
            <div class="flex justify-between items-center mb-6">
                <h3 class="heading-secondary text-xl">Progress Report</h3>
                <button onclick="this.closest('.fixed').remove()" class="text-gray-500 hover:text-gray-700">
                    <span class="text-2xl">&times;</span>
                </button>
            </div>
            
            <div class="space-y-4">
                <div class="bg-gray-50 p-4 rounded-lg">
                    <div class="grid grid-cols-2 gap-4 text-center">
                        <div>
                            <div class="text-2xl font-bold text-gray-800">${totalGoals}</div>
                            <div class="text-sm text-gray-600">Total Goals</div>
                        </div>
                        <div>
                            <div class="text-2xl font-bold text-green-600">${completedGoals}</div>
                            <div class="text-sm text-gray-600">Completed</div>
                        </div>
                        <div>
                            <div class="text-2xl font-bold text-blue-600">${activeGoals}</div>
                            <div class="text-sm text-gray-600">Active</div>
                        </div>
                        <div>
                            <div class="text-2xl font-bold text-indigo-600">${avgProgress}%</div>
                            <div class="text-sm text-gray-600">Avg Progress</div>
                        </div>
                    </div>
                </div>
                
                <div class="text-center">
                    <button onclick="viewHistory(); this.closest('.fixed').remove()" class="btn-primary px-6 py-2">
                        View Detailed History
                    </button>
                </div>
            </div>
        </div>
    `;
    
    document.body.appendChild(modal);
}

function editGoal(goalId) {
    const goal = goals.find(g => g.id === goalId);
    if (!goal) {
        authUtils.showErrorMessage('Goal not found');
        return;
    }
    
    // Prevent background scrolling
    document.body.classList.add('modal-open');
    
    // Show modal first
    document.getElementById('edit-goal-modal').classList.remove('hidden');
    
    // Setup event listeners for this modal instance (this clones the form, so do it first)
    setupEditModalEventListeners();
    
    // Populate the edit form AFTER event listeners are set up
    document.getElementById('edit-goal-id').value = goal.id;
    document.getElementById('edit-goal-title').value = goal.title;
    document.getElementById('edit-goal-description').value = goal.description || '';
    document.getElementById('edit-goal-target-date').value = goal.target_date || '';
    document.getElementById('edit-goal-status').value = goal.status;
    
    // Load subgoals
    loadSubgoalsForEdit(goal.subgoals || []);
    
    // Initialize tag selector with current goal tags
    editSelectedTagIds = goal.tags ? goal.tags.map(tag => tag.id) : [];
    renderTagSelector('edit-goal-tags-grid', editSelectedTagIds);
}

// Setup event listeners specifically for the edit modal
function setupEditModalEventListeners() {
    console.log('🎯 Setting up edit modal event listeners...'); // Debug log
    
    // Remove any existing listeners to prevent duplicates
    const editForm = document.getElementById('edit-goal-form');
    const updateBtn = document.getElementById('update-goal-btn');
    
    if (editForm) {
        // Clone and replace to remove existing listeners
        const newEditForm = editForm.cloneNode(true);
        editForm.parentNode.replaceChild(newEditForm, editForm);
        
        // Add form submit listener
        newEditForm.addEventListener('submit', async function(e) {
            e.preventDefault();
            console.log('✅ Edit goal form submitted via form event'); // Debug log
            await handleGoalUpdate();
        });
        
        console.log('📝 Form submit listener attached'); // Debug log
    } else {
        console.error('❌ Edit goal form not found!');
    }
    
    if (updateBtn) {
        // Clone and replace to remove existing listeners
        const newUpdateBtn = updateBtn.cloneNode(true);
        updateBtn.parentNode.replaceChild(newUpdateBtn, updateBtn);
        
        // Add button click listener
        newUpdateBtn.addEventListener('click', async function(e) {
            e.preventDefault();
            console.log('✅ Update button clicked directly'); // Debug log
            await handleGoalUpdate();
        });
        
        console.log('🔘 Button click listener attached'); // Debug log
    } else {
        console.error('❌ Update goal button not found!');
    }
    
    // Add ESC key listener to close modal
    const handleEscKey = function(e) {
        if (e.key === 'Escape' || e.keyCode === 27) {
            const editModal = document.getElementById('edit-goal-modal');
            // Only close if the edit modal is visible (not hidden)
            if (editModal && !editModal.classList.contains('hidden')) {
                console.log('🎯 ESC key pressed - closing edit modal'); // Debug log
                closeEditGoalModal();
            }
        }
    };
    
    // Remove any existing ESC listeners and add new one
    document.removeEventListener('keydown', window.editModalEscHandler);
    window.editModalEscHandler = handleEscKey;
    document.addEventListener('keydown', handleEscKey);
    
    console.log('⌨️ ESC key listener attached to edit modal'); // Debug log
}

window.closeEditGoalModal = function() {
    const editModal = document.getElementById('edit-goal-modal');
    const subgoalModal = document.getElementById('subgoal-creator-modal');
    
    // Re-enable background scrolling
    document.body.classList.remove('modal-open');
    
    // Remove ESC key listener when closing modal
    if (window.editModalEscHandler) {
        document.removeEventListener('keydown', window.editModalEscHandler);
        window.editModalEscHandler = null;
        console.log('⌨️ ESC key listener removed'); // Debug log
    }
    
    // Close both modals
    editModal.classList.add('hidden');
    if (subgoalModal) {
        subgoalModal.classList.add('hidden');
    }
    
    // Reset visibility
    editModal.style.visibility = 'visible';
    
    // Reset forms
    document.getElementById('edit-goal-form').reset();
    document.getElementById('subgoals-container').innerHTML = '';
    
    // Reset inline form if it exists
    const inlineForm = document.getElementById('inline-subgoal-form');
    if (inlineForm) {
        inlineForm.classList.add('hidden');
        document.getElementById('inline-subgoal-title').value = '';
        document.getElementById('inline-subgoal-description').value = '';
        document.getElementById('inline-subgoal-target-date').value = '';
        
        // Reset button
        const btn = document.getElementById('add-subgoal-btn');
        if (btn) {
            btn.innerHTML = '<i class="fas fa-plus mr-1"></i> Add Sub-goal';
            btn.onclick = toggleInlineSubgoalForm;
        }
    }
    
    // Clear subgoal creator form if it was open
    const newSubgoalTitle = document.getElementById('new-subgoal-title');
    if (newSubgoalTitle) {
        newSubgoalTitle.value = '';
        document.getElementById('new-subgoal-description').value = '';
        document.getElementById('new-subgoal-target-date').value = '';
    }
}

function loadSubgoalsForEdit(subgoals) {
    const container = document.getElementById('subgoals-container');
    const emptyState = document.getElementById('subgoals-empty-state');
    
    container.innerHTML = '';
    
    if (subgoals.length === 0) {
        emptyState.classList.remove('hidden');
    } else {
        emptyState.classList.add('hidden');
        subgoals.forEach(subgoal => {
            addSubgoalToList(subgoal);
        });
    }
}

window.addSubgoalToList = function(subgoal = null) {
    const container = document.getElementById('subgoals-container');
    const emptyState = document.getElementById('subgoals-empty-state');
    
    // Hide empty state
    emptyState.classList.add('hidden');
    
    const row = document.createElement('div');
    row.className = 'subgoal-item modern-card border rounded-md p-2 hover:border-gray-300 transition-all';
    row.innerHTML = `
        <input type="hidden" class="subgoal-id" value="${subgoal?.id || ''}">
        <div class="flex items-start space-x-2">
            <input type="checkbox" 
                   class="form-checkbox subgoal-checkbox mt-0.5 w-3 h-3" 
                   ${subgoal?.status === 'achieved' ? 'checked' : ''}
                   onchange="toggleSubgoalStatus(this)"
                   ${!subgoal?.id ? 'disabled' : ''}>
            <div class="flex-1">
                <input type="text" 
                       class="subgoal-title input-field w-full mb-1 text-xs py-1 ${subgoal?.status === 'achieved' ? 'line-through text-gray-500' : ''}" 
                       value="${subgoal?.title || ''}" 
                       placeholder="Enter sub-goal title" 
                       required>
                <textarea class="subgoal-description input-field w-full text-xs py-1" 
                          rows="1" 
                          placeholder="Description (optional)">${subgoal?.description || ''}</textarea>
                ${subgoal?.target_date ? `
                    <input type="date" 
                           class="subgoal-target-date input-field w-full text-xs py-1 mt-1" 
                           value="${subgoal.target_date}">
                ` : `
                    <input type="date" 
                           class="subgoal-target-date input-field w-full text-xs py-1 mt-1" 
                           placeholder="Target date (optional)">
                `}
                <input type="hidden" class="subgoal-status" value="${subgoal?.status || 'pending'}">
            </div>
            <button type="button" onclick="removeSubgoalFromList(this)" class="text-red-500 hover:text-red-700 p-1 rounded hover:bg-red-50 transition-colors" title="Remove sub-goal">
                <i class="fas fa-trash text-xs"></i>
            </button>
        </div>
    `;
    
    container.appendChild(row);
    
    // Scroll to the new item within the subgoals container
    const scrollContainer = container.closest('.subgoals-scroll-area');
    if (scrollContainer) {
        // Scroll the container to show the new item
        setTimeout(() => {
            row.scrollIntoView({ 
                behavior: 'smooth', 
                block: 'nearest',
                inline: 'nearest'
            });
        }, 100);
    }
    
    // Focus on the title input after a brief delay
    setTimeout(() => {
        const titleInput = row.querySelector('.subgoal-title');
        if (titleInput) {
            titleInput.focus();
        }
    }, 200);
}

function toggleSubgoalStatus(checkbox) {
    const row = checkbox.closest('.subgoal-item');
    const titleInput = row.querySelector('.subgoal-title');
    const statusInput = row.querySelector('.subgoal-status');
    
    if (checkbox.checked) {
        titleInput.classList.add('line-through', 'text-gray-500');
        statusInput.value = 'achieved';
        row.style.background = '#f0fdf4';
        setTimeout(() => {
            row.style.background = '';
        }, 1000);
    } else {
        titleInput.classList.remove('line-through', 'text-gray-500');
        statusInput.value = 'pending';
    }
}

function removeSubgoalFromList(button) {
    const container = document.getElementById('subgoals-container');
    const emptyState = document.getElementById('subgoals-empty-state');
    
    button.closest('.subgoal-item').remove();
    
    // Show empty state if no subgoals left
    if (container.children.length === 0) {
        emptyState.classList.remove('hidden');
    }
}

// Update goal function
async function updateGoal(goalData) {
    try {
        console.log('🌐 Making API request to update goal:', goalData.id); // Debug log
        
        const response = await fetch(`/api/goals/${goalData.id}`, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(goalData),
            credentials: 'include'
        });
        
        console.log('📡 API response status:', response.status); // Debug log
        
        if (response.ok) {
            const updatedGoal = await response.json();
            console.log('✅ Goal updated successfully:', updatedGoal); // Debug log
            return updatedGoal;
        } else {
            const error = await response.json();
            console.error('❌ API error response:', error); // Debug log
            throw new Error(error.error || 'Failed to update goal');
        }
    } catch (error) {
        console.error('❌ Network error updating goal:', error);
        throw error;
    }
}

// Handle subgoal updates
async function updateSubgoals(goalId, subgoalRows) {
    const promises = [];
    
    console.log(`🔍 Processing ${subgoalRows.length} subgoal rows for goal ${goalId}`); // Debug log
    
    subgoalRows.forEach((row, index) => {
        const subgoalIdElement = row.querySelector('.subgoal-id');
        const titleElement = row.querySelector('.subgoal-title');
        const descriptionElement = row.querySelector('.subgoal-description');
        const targetDateElement = row.querySelector('.subgoal-target-date');
        const statusElement = row.querySelector('.subgoal-status');
        
        if (!subgoalIdElement || !titleElement || !descriptionElement || !targetDateElement || !statusElement) {
            console.error(`❌ Missing subgoal form elements in row ${index + 1}`);
            console.log('Row HTML:', row.innerHTML);
            return; // Skip this row
        }
        
        const subgoalId = subgoalIdElement.value;
        const title = titleElement.value.trim();
        const description = descriptionElement.value.trim();
        const targetDate = targetDateElement.value;
        const status = statusElement.value;
        
        console.log(`📋 Subgoal ${index + 1}:`, { subgoalId, title, description, targetDate, status }); // Debug log
        
        if (!title) {
            console.log(`⚠️ Skipping subgoal ${index + 1} - no title`); // Debug log
            return; // Skip empty subgoals
        }
        
        const subgoalData = { title, description, status };
        if (targetDate) {
            subgoalData.target_date = targetDate;
        }
        
        if (subgoalId) {
            // Update existing subgoal
            console.log(`🔄 Updating existing subgoal ${subgoalId}`); // Debug log
            promises.push(
                fetch(`/api/subgoals/${subgoalId}`, {
                    method: 'PUT',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(subgoalData),
                    credentials: 'include'
                }).then(response => {
                    console.log(`📡 Update subgoal ${subgoalId} response:`, response.status); // Debug log
                    return response;
                })
            );
        } else {
            // Create new subgoal
            console.log(`➕ Creating new subgoal for goal ${goalId}`); // Debug log
            promises.push(
                fetch(`/api/goals/${goalId}/subgoals`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(subgoalData),
                    credentials: 'include'
                }).then(response => {
                    console.log(`📡 Create subgoal response:`, response.status); // Debug log
                    return response;
                })
            );
        }
    });
    
    if (promises.length > 0) {
        console.log(`🚀 Executing ${promises.length} subgoal operations...`); // Debug log
        const results = await Promise.all(promises);
        console.log('✅ All subgoal operations completed:', results.map(r => r.status)); // Debug log
    } else {
        console.log('ℹ️ No subgoal operations to perform'); // Debug log
    }
}

// Quick update subgoal from main list
async function quickUpdateSubgoal(subgoalId, isChecked, goalId) {
    try {
        // Show loading feedback
        const checkbox = event.target;
        const subgoalItem = checkbox.closest('.subgoal-item');
        const originalText = subgoalItem.querySelector('span').textContent;
        
        // Add loading state
        subgoalItem.style.opacity = '0.6';
        subgoalItem.querySelector('span').textContent = 'Updating...';
        
        const status = isChecked ? 'achieved' : 'pending';
        const response = await fetch(`/api/subgoals/${subgoalId}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ status }),
            credentials: 'include'
        });
        
        if (response.ok) {
            // Update local state immediately for better UX
            const goal = goals.find(g => g.id === goalId);
            if (goal) {
                const subgoal = goal.subgoals.find(sg => sg.id === subgoalId);
                if (subgoal) {
                    subgoal.status = status;
                    // Recalculate goal progress
                    const completedSubgoals = goal.subgoals.filter(sg => sg.status === 'achieved').length;
                    goal.progress = goal.subgoals.length > 0 ? Math.round((completedSubgoals / goal.subgoals.length) * 100) : 0;
                    
                    // Auto-update goal status based on new system: Created -> Started -> Working -> Completed
                    const previousStatus = goal.status;
                    if (goal.progress === 100 && goal.status !== 'completed') {
                        goal.status = 'completed';
                    } else if (completedSubgoals === 1 && goal.status === 'created') {
                        goal.status = 'started';
                    } else if (completedSubgoals >= 2 && (goal.status === 'created' || goal.status === 'started')) {
                        goal.status = 'working';
                    } else if (goal.progress === 0) {
                        goal.status = 'created';
                    }
                    
                    // Update goal status on backend if it changed
                    if (goal.status !== previousStatus) {
                        fetch(`/api/goals/${goalId}`, {
                            method: 'PUT',
                            headers: { 'Content-Type': 'application/json' },
                            body: JSON.stringify({ status: goal.status }),
                            credentials: 'include'
                        }).catch(error => {
                            console.error('Failed to update goal status:', error);
                        });
                    }
                }
            }
            
            // Restore original state and apply new styling
            subgoalItem.style.opacity = '1';
            subgoalItem.querySelector('span').textContent = originalText;
            
            // Update visual state
            const span = subgoalItem.querySelector('span');
            if (isChecked) {
                span.classList.add('line-through', 'text-gray-500');
                span.classList.remove('text-gray-700', 'font-medium');
                authUtils.showSuccessMessage('Sub-goal completed!');
                
                // Add completion effect
                subgoalItem.style.background = '#f0fdf4';
                setTimeout(() => {
                    subgoalItem.style.background = '';
                }, 1000);
            } else {
                span.classList.remove('line-through', 'text-gray-500');
                span.classList.add('text-gray-700', 'font-medium');
            }
            
            // Update progress bar
            updateGoalProgressBar(goalId);
            
            // Update stats display
            const statsResponse = await fetch('/api/dashboard/stats', { credentials: 'include' });
            if (statsResponse.ok) {
                const stats = await statsResponse.json();
                updateStatsDisplay(stats);
                updateProgressChart(stats);
            }
            
            // Reload goals to get updated timestamps for proper sorting
            const goalsResponse = await fetch('/api/goals', { credentials: 'include' });
            if (goalsResponse.ok) {
                goals = await goalsResponse.json();
                renderGoals();
            }
            
        } else {
            // Restore original state on error
            subgoalItem.style.opacity = '1';
            subgoalItem.querySelector('span').textContent = originalText;
            checkbox.checked = !isChecked; // Revert checkbox
            authUtils.showErrorMessage('Failed to update sub-goal');
        }
    } catch (error) {
        console.error('Error updating subgoal:', error);
        // Restore original state on error
        const subgoalItem = checkbox.closest('.subgoal-item');
        subgoalItem.style.opacity = '1';
        checkbox.checked = !isChecked; // Revert checkbox
        authUtils.showErrorMessage('Connection error. Please try again');
    }
}

// Function to toggle subgoal checkbox when clicking on title (grid view)
window.toggleSubgoalCheckbox = function(subgoalId, goalId) {
    const checkbox = document.getElementById(`subgoal-${subgoalId}`);
    if (checkbox) {
        checkbox.checked = !checkbox.checked;
        quickUpdateSubgoal(subgoalId, checkbox.checked, goalId);
    }
}

// Function to toggle subgoal checkbox when clicking on title (list view)
window.toggleSubgoalCheckboxList = function(subgoalId, goalId) {
    const checkbox = document.getElementById(`subgoal-list-${subgoalId}`);
    if (checkbox) {
        checkbox.checked = !checkbox.checked;
        quickUpdateSubgoal(subgoalId, checkbox.checked, goalId);
    }
}

// Handle keypress in quick subgoal input
window.handleQuickSubgoalKeypress = function(event, goalId) {
    if (event.key === 'Enter') {
        event.preventDefault();
        quickAddSubgoal(goalId);
    }
}

// Maintain sticky hover when focusing on input
window.maintainStickyHover = function(goalId) {
    const card = document.querySelector(`[data-goal-id="${goalId}"]`);
    if (card) {
        card.classList.add('sticky-hover');
        stickyHoverStates.set(goalId.toString(), true);
    }
}

// Quick add subgoal function
async function quickAddSubgoal(goalId) {
    try {
        const input = document.getElementById(`quick-subgoal-${goalId}`);
        const title = input.value.trim();
        
        if (!title) {
            authUtils.showErrorMessage('Please enter a sub-goal title');
            input.focus();
            return;
        }
        
        // Find the goal to inherit target_date
        const goal = goals.find(g => g.id === goalId);
        if (!goal) {
            authUtils.showErrorMessage('Goal not found');
            return;
        }
        
        // Show loading state
        input.disabled = true;
        input.value = 'Adding...';
        
        // Prepare subgoal data
        const subgoalData = {
            title: title,
            description: '',
            target_date: goal.target_date || null,
            status: 'pending'
        };
        
        // Call API to create subgoal
        const response = await fetch(`/api/goals/${goalId}/subgoals`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(subgoalData),
            credentials: 'include'
        });
        
        if (response.ok) {
            const newSubgoal = await response.json();
            
            // Clear input and restore state
            input.value = '';
            input.disabled = false;
            input.placeholder = 'Add quick sub-goal...';
            
            // Show success message
            authUtils.showSuccessMessage(`Sub-goal "${title}" added successfully`);
            
            // Reload goals to get updated data and maintain sorting
            const goalsResponse = await fetch('/api/goals', { credentials: 'include' });
            if (goalsResponse.ok) {
                goals = await goalsResponse.json();
                renderGoals();
            }
            
            // Update stats
            const statsResponse = await fetch('/api/dashboard/stats', { credentials: 'include' });
            if (statsResponse.ok) {
                const stats = await statsResponse.json();
                updateStatsDisplay(stats);
                updateProgressChart(stats);
            }
            
        } else {
            const error = await response.json();
            
            // Restore input state
            input.value = title;
            input.disabled = false;
            input.focus();
            
            authUtils.showErrorMessage(error.error || 'Failed to add sub-goal');
        }
        
    } catch (error) {
        console.error('Error adding quick subgoal:', error);
        
        // Restore input state
        const input = document.getElementById(`quick-subgoal-${goalId}`);
        if (input) {
            input.disabled = false;
            input.focus();
        }
        
        authUtils.showErrorMessage('Connection error. Please try again');
    }
}

// Update goal progress after subgoal change
function updateGoalProgressBar(goalId) {
    const goal = goals.find(g => g.id === goalId);
    if (!goal) return;
    
    // Find the goal card by data attribute
    const goalCard = document.querySelector(`[data-goal-id="${goalId}"]`);
    if (!goalCard) return;
    
    // Update conic-gradient progress circle
    const progressCircle = goalCard.querySelector('.progress-circle > div');
    if (progressCircle) {
        const progressColor = goal.progress >= 100 ? '#10b981' : 
                             goal.progress >= 75 ? '#3b82f6' : 
                             goal.progress >= 25 ? '#f59e0b' : '#ef4444';
        
        // Use CSS variable-aware background color for dark mode compatibility
        const isDarkMode = document.documentElement.getAttribute('data-theme') === 'dark';
        const backgroundColor = isDarkMode ? '#475569' : '#f3f4f6'; // --color-border-primary in dark mode
        
        progressCircle.style.background = `conic-gradient(${progressColor} ${goal.progress * 3.6}deg, ${backgroundColor} ${goal.progress * 3.6}deg)`;
    }
    
    // Update progress text
    const progressText = goalCard.querySelector('.progress-text');
    if (progressText) {
        progressText.textContent = `${Math.round(goal.progress)}%`;
    }
    
    // Update subgoals completion badge
    const completionBadge = goalCard.querySelector('.text-xs.bg-blue-100');
    if (completionBadge) {
        const completed = goal.subgoals.filter(sg => sg.status === 'achieved').length;
        completionBadge.textContent = `${completed}/${goal.subgoals.length}`;
    }
    
    // Update status badge if goal status changed
    const statusBadge = goalCard.querySelector('.status-badge');
    if (statusBadge) {
        statusBadge.className = `status-badge ${getStatusBadgeClass(goal.status)} flex-shrink-0 ml-2`;
        statusBadge.setAttribute('title', goal.status.replace('_', ' ').toUpperCase());
        const icon = statusBadge.querySelector('i');
        if (icon) {
            icon.className = `fas ${getStatusIcon(goal.status)}`;
        }
    }
}

// History reporting function removed - now using window.viewHistory

function showHistoryModal(historyData) {
    const modal = document.createElement('div');
    modal.className = 'fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50';
    modal.innerHTML = `
        <div class="modern-card p-8 rounded-xl shadow-2xl max-w-4xl w-full mx-4 max-h-[90vh] overflow-y-auto">
            <div class="flex justify-between items-center mb-6">
                <h3 class="heading-secondary text-xl">Achievement History</h3>
                <button onclick="this.closest('.fixed').remove()" class="text-gray-500 hover:text-gray-700">
                    <span class="text-2xl">&times;</span>
                </button>
            </div>
            
            <div class="grid grid-cols-1 md:grid-cols-2 gap-6 mb-6">
                <div class="bg-gray-50 p-4 rounded-lg">
                    <h4 class="font-semibold text-gray-800 mb-2">Achievement Summary</h4>
                    <p class="text-gray-600">Total Achievements: ${historyData.total_achievements}</p>
                </div>
                
                <div class="bg-gray-50 p-4 rounded-lg">
                    <h4 class="font-semibold text-gray-800 mb-2">Timing Analysis</h4>
                    <p class="text-gray-600">
                        Early: ${historyData.timing_analysis.filter(t => t.status === 'early').length} | 
                        On Time: ${historyData.timing_analysis.filter(t => t.status === 'on_time').length} | 
                        Late: ${historyData.timing_analysis.filter(t => t.status === 'late').length}
                    </p>
                </div>
            </div>
            
            <div class="space-y-4">
                ${historyData.completed_goals.map(goal => `
                    <div class="border border-gray-200 rounded-lg p-4">
                        <div class="flex justify-between items-start">
                            <div class="flex-1">
                                <h4 class="font-semibold text-gray-800">${goal.title}</h4>
                                <p class="text-gray-600 text-sm">${goal.description || 'No description'}</p>
                                <div class="flex space-x-4 text-sm text-gray-500 mt-2">
                                    <span>Target: ${goal.target_date ? parseLocalDate(goal.target_date).toLocaleDateString() : 'No date'}</span>
                                    <span>Achieved: ${goal.achieved_date ? parseLocalDate(goal.achieved_date).toLocaleDateString() : 'Unknown'}</span>
                                </div>
                            </div>
                            <div class="text-right">
                                <span class="inline-block px-3 py-1 rounded-full text-sm font-medium bg-green-100 text-green-800">
                                    Completed
                                </span>
                            </div>
                        </div>
                    </div>
                `).join('')}
            </div>
        </div>
    `;
    
    document.body.appendChild(modal);
}

// Setup event listeners
function setupEventListeners() {
    // Create goal form submission
    document.getElementById('create-goal-form').addEventListener('submit', async function(e) {
        e.preventDefault();
        
        const goalData = {
            title: document.getElementById('goal-title').value,
            description: document.getElementById('goal-description').value,
            target_date: document.getElementById('goal-target-date').value
        };
        
        if (!goalData.title.trim()) {
            authUtils.showErrorMessage('Please enter a goal title');
            return;
        }
        
        await createGoal(goalData);
    });
    
    // Note: Edit goal form listeners are now set up when the modal opens
}

// Direct handler for onclick - make it globally accessible
window.handleGoalUpdateDirect = async function() {
    console.log('🎯 Direct onclick handler called!'); // Debug log
    await handleGoalUpdate();
}

// Centralized goal update handler
async function handleGoalUpdate() {
    console.log('🔄 Starting goal update process...'); // Debug log
    
    try {
        const goalIdElement = document.getElementById('edit-goal-id');
        const titleElement = document.getElementById('edit-goal-title');
        const descriptionElement = document.getElementById('edit-goal-description');
        const targetDateElement = document.getElementById('edit-goal-target-date');
        const statusElement = document.getElementById('edit-goal-status');
        
        if (!goalIdElement || !titleElement || !descriptionElement || !targetDateElement || !statusElement) {
            console.error('❌ Missing form elements');
            if (window.authUtils) {
                window.authUtils.showErrorMessage('Form elements not found. Please refresh the page.');
            } else {
                alert('Form elements not found. Please refresh the page.');
            }
            return;
        }
        
        const goalId = goalIdElement.value;
        const goalData = {
            id: goalId,
            title: titleElement.value,
            description: descriptionElement.value,
            target_date: targetDateElement.value,
            status: statusElement.value
        };
        
        console.log('📝 Goal data to update:', goalData); // Debug log
        
        if (!goalData.title.trim()) {
            if (window.authUtils) {
                window.authUtils.showErrorMessage('Please enter a goal title');
            } else {
                alert('Please enter a goal title');
            }
            return;
        }
        
        if (!goalId) {
            if (window.authUtils) {
                window.authUtils.showErrorMessage('Goal ID is missing. Please close and reopen the modal.');
            } else {
                alert('Goal ID is missing. Please close and reopen the modal.');
            }
            return;
        }
        
        // Show loading state
        let updateBtn = document.getElementById('update-goal-btn');
        if (updateBtn) {
            const originalText = updateBtn.innerHTML;
            updateBtn.innerHTML = '<i class="fas fa-spinner fa-spin mr-2"></i> Updating...';
            updateBtn.disabled = true;
        }
        
        // Update subgoals first - exclude the inline form
        const subgoalRows = document.querySelectorAll('.subgoal-item:not(#inline-subgoal-form)');
        console.log(`📋 Found ${subgoalRows.length} subgoal rows to process`); // Debug log
        
        if (subgoalRows.length > 0) {
            console.log('🔄 Updating subgoals...'); // Debug log
            await updateSubgoals(goalId, subgoalRows);
            console.log('✅ Subgoals updated successfully'); // Debug log
        }
        
        // Update goal
        console.log('🔄 Updating main goal...'); // Debug log
        await updateGoal(goalData);
        console.log('✅ Goal updated successfully'); // Debug log
        
        // Update goal tags
        console.log('🔄 Updating goal tags...'); // Debug log
        console.log('📌 Current editSelectedTagIds:', editSelectedTagIds);
        console.log('📌 Available tags:', tags);
        await updateGoalTags(goalId, editSelectedTagIds);
        console.log('✅ Goal tags updated successfully'); // Debug log
        
        // Reload dashboard data to show updated tags
        console.log('🔄 Reloading dashboard data with updated tags...'); // Debug log
        await loadDashboardData();
        console.log('✅ Dashboard data reloaded successfully'); // Debug log
        
        // Close modal and show success message
        closeEditGoalModal();
        if (window.authUtils) {
            window.authUtils.showSuccessMessage('Goal updated successfully');
        } else {
            alert('Goal updated successfully');
        }
        
        // Restore button state
        updateBtn = document.getElementById('update-goal-btn');
        if (updateBtn) {
            updateBtn.innerHTML = '<i class="fas fa-save mr-2"></i> Update Goal';
            updateBtn.disabled = false;
        }
        
    } catch (error) {
        console.error('❌ Error in goal update process:', error);
        if (window.authUtils) {
            window.authUtils.showErrorMessage(`Failed to update goal: ${error.message}`);
        } else {
            alert(`Failed to update goal: ${error.message}`);
        }
        
        // Restore button state
        updateBtn = document.getElementById('update-goal-btn');
        if (updateBtn) {
            updateBtn.innerHTML = '<i class="fas fa-save mr-2"></i> Update Goal';
            updateBtn.disabled = false;
        }
    }
}

// Enhanced filtering and sorting functionality
function setupFiltersAndSorting() {
    const searchInput = document.getElementById('goal-search');
    
    if (searchInput) {
        searchInput.addEventListener('input', (e) => {
            currentPage = 0;
            renderGoals();
            saveUserSettings();
        });
    }
    
    // Close dropdowns when clicking outside
    document.addEventListener('click', (e) => {
        if (!e.target.closest('#filter-dropdown-btn') && !e.target.closest('#filter-dropdown')) {
            closeFilterDropdown();
        }
        if (!e.target.closest('#sort-dropdown-btn') && !e.target.closest('#sort-dropdown')) {
            closeSortDropdown();
        }
        if (!e.target.closest('#tag-filter-dropdown-btn') && !e.target.closest('#tag-filter-dropdown')) {
            closeTagFilterDropdown();
        }
    });
}

function applyFiltersAndSort() {
    let filtered = [...goals];
    
    // Apply search filter
    const searchTerm = document.getElementById('goal-search')?.value.toLowerCase() || '';
    if (searchTerm) {
        filtered = filtered.filter(goal => 
            goal.title.toLowerCase().includes(searchTerm) ||
            goal.description?.toLowerCase().includes(searchTerm) ||
            goal.subgoals.some(sg => sg.title.toLowerCase().includes(searchTerm))
        );
    }
    
    // Apply status filter
    if (currentFilter !== 'all') {
        filtered = filtered.filter(goal => goal.status === currentFilter);
    }
    
    // Apply tag filter
    if (currentTagFilter !== null) {
        filtered = filtered.filter(goal => 
            goal.tags && goal.tags.some(tag => tag.id === currentTagFilter)
        );
    }
    
    // Apply sorting
    filtered.sort((a, b) => {
        switch (currentSort) {
            case 'recent':
                // Use last_activity_at for more accurate "recently updated" sorting
                const aTimestamp = a.last_activity_at || a.updated_at || a.created_at;
                const bTimestamp = b.last_activity_at || b.updated_at || b.created_at;
                return parseLocalDate(bTimestamp) - parseLocalDate(aTimestamp);
            case 'target':
                if (!a.target_date && !b.target_date) return 0;
                if (!a.target_date) return 1;
                if (!b.target_date) return -1;
                return parseLocalDate(a.target_date) - parseLocalDate(b.target_date);
            case 'urgent_subgoals':
                // Helper function to find earliest subgoal date
                const getEarliestSubgoalDate = (goal) => {
                    if (!goal.subgoals || goal.subgoals.length === 0) return null;
                    
                    const dates = goal.subgoals
                        .filter(sg => sg.target_date && sg.status !== 'achieved')
                        .map(sg => parseLocalDate(sg.target_date));
                    
                    if (dates.length === 0) return null;
                    
                    return new Date(Math.min(...dates));
                };
                
                const aEarliest = getEarliestSubgoalDate(a);
                const bEarliest = getEarliestSubgoalDate(b);
                
                // Goals with no subgoal dates go to the bottom
                if (!aEarliest && !bEarliest) return 0;
                if (!aEarliest) return 1;
                if (!bEarliest) return -1;
                
                // Sort by earliest date (ascending - most urgent first)
                return aEarliest - bEarliest;
            case 'progress':
                return b.progress - a.progress;
            case 'name':
                return a.title.localeCompare(b.title);
            default:
                return 0;
        }
    });
    
    filteredGoals = filtered;
}

// Modern dropdown functionality
window.toggleFilterDropdown = function() {
    const dropdown = document.getElementById('filter-dropdown');
    const btn = document.getElementById('filter-dropdown-btn');
    const chevron = document.getElementById('filter-chevron');
    
    if (dropdown && dropdown.classList.contains('hidden')) {
        dropdown.classList.remove('hidden');
        btn.classList.add('active');
        chevron.style.transform = 'rotate(180deg)';
        closeSortDropdown(); // Close other dropdown
    } else {
        closeFilterDropdown();
    }
}

window.toggleSortDropdown = function() {
    const dropdown = document.getElementById('sort-dropdown');
    const btn = document.getElementById('sort-dropdown-btn');
    const chevron = document.getElementById('sort-chevron');
    
    if (dropdown.classList.contains('hidden')) {
        dropdown.classList.remove('hidden');
        btn.classList.add('active');
        chevron.style.transform = 'rotate(180deg)';
        closeFilterDropdown(); // Close other dropdown
    } else {
        closeSortDropdown();
    }
}

function closeFilterDropdown() {
    const dropdown = document.getElementById('filter-dropdown');
    const btn = document.getElementById('filter-dropdown-btn');
    const chevron = document.getElementById('filter-chevron');
    
    if (dropdown && !dropdown.classList.contains('hidden')) {
        dropdown.classList.add('hidden');
        btn.classList.remove('active');
        chevron.style.transform = 'rotate(0deg)';
    }
}

function closeSortDropdown() {
    const dropdown = document.getElementById('sort-dropdown');
    const btn = document.getElementById('sort-dropdown-btn');
    const chevron = document.getElementById('sort-chevron');
    
    if (dropdown && !dropdown.classList.contains('hidden')) {
        dropdown.classList.add('hidden');
        btn.classList.remove('active');
        chevron.style.transform = 'rotate(0deg)';
    }
}

window.setFilter = function(filterValue) {
    currentFilter = filterValue;
    currentPage = 0;
    
    // Update label
    const label = document.getElementById('filter-label');
    const filterLabels = {
        'all': 'All Goals',
        'created': 'Created',
        'started': 'Started',
        'working': 'Working',
        'completed': 'Completed'
    };
    
    if (label) {
        label.textContent = filterLabels[filterValue];
    }
    
    closeFilterDropdown();
    renderGoals();
    saveUserSettings();
}

window.setSort = function(sortValue) {
    currentSort = sortValue;
    currentPage = 0;
    
    // Update label
    const label = document.getElementById('sort-label');
    const sortLabels = {
        'recent': 'Recently Updated',
        'target': 'Target Date',
        'progress': 'Progress',
        'name': 'Name',
        'urgent_subgoals': 'Due Date'
    };
    label.textContent = sortLabels[sortValue];
    
    closeSortDropdown();
    renderGoals();
    saveUserSettings();
}

// Enhanced view mode management
window.setViewMode = function(mode) {
    currentViewMode = mode;
    
    // Update button states
    const gridBtn = document.getElementById('grid-view-btn');
    const listBtn = document.getElementById('list-view-btn');
    
    // Remove active class from both
    gridBtn.classList.remove('active', 'bg-white', 'text-gray-700', 'shadow-sm');
    listBtn.classList.remove('active', 'bg-white', 'text-gray-700', 'shadow-sm');
    gridBtn.classList.add('text-gray-500');
    listBtn.classList.add('text-gray-500');
    
    if (mode === 'grid') {
        gridBtn.classList.add('active', 'view-toggle-btn', 'shadow-sm');
        gridBtn.classList.remove('text-gray-500');
    } else {
        listBtn.classList.add('active', 'view-toggle-btn', 'shadow-sm');
        listBtn.classList.remove('text-gray-500');
    }
    
    renderGoals();
    saveUserSettings();
}

// Tag filter functions
window.toggleTagFilterDropdown = function() {
    const dropdown = document.getElementById('tag-filter-dropdown');
    const btn = document.getElementById('tag-filter-dropdown-btn');
    const chevron = document.getElementById('tag-filter-chevron');
    
    if (dropdown.classList.contains('hidden')) {
        dropdown.classList.remove('hidden');
        btn.classList.add('active');
        chevron.style.transform = 'rotate(180deg)';
        closeFilterDropdown(); // Close other dropdowns
        closeSortDropdown();
    } else {
        closeTagFilterDropdown();
    }
}

function closeTagFilterDropdown() {
    const dropdown = document.getElementById('tag-filter-dropdown');
    const btn = document.getElementById('tag-filter-dropdown-btn');
    const chevron = document.getElementById('tag-filter-chevron');
    
    if (dropdown && !dropdown.classList.contains('hidden')) {
        dropdown.classList.add('hidden');
        btn.classList.remove('active');
        chevron.style.transform = 'rotate(0deg)';
    }
}

window.setTagFilter = function(tagId) {
    currentTagFilter = tagId;
    currentPage = 0;
    
    // Update label
    const label = document.getElementById('tag-filter-label');
    if (tagId === null) {
        label.textContent = 'All Tags';
    } else {
        const tag = tags.find(t => t.id === tagId);
        label.textContent = tag ? tag.name : 'Unknown Tag';
    }
    
    // Update selection state in dropdown
    document.querySelectorAll('.tag-filter-option').forEach(option => {
        option.classList.remove('selected');
    });
    
    const selectedOption = tagId === null ? 
        document.querySelector('.tag-filter-option') : 
        document.querySelector(`[data-tag-id="${tagId}"]`);
    if (selectedOption) {
        selectedOption.classList.add('selected');
    }
    
    closeTagFilterDropdown();
    renderGoals();
    saveUserSettings();
}

window.clearTagFilter = function() {
    setTagFilter(null);
}

function populateTagFilterDropdown() {
    const container = document.getElementById('tag-filter-options');
    if (!container) return;
    
    if (tags.length === 0) {
        container.innerHTML = `
            <div class="px-4 py-2 text-sm text-gray-500 text-center">
                <p>No tags available</p>
                <button type="button" onclick="showTagManagementModal(); closeTagFilterDropdown();" class="text-blue-600 hover:text-blue-800 underline text-xs mt-1">
                    Create your first tag
                </button>
            </div>
        `;
        return;
    }
    
    container.innerHTML = tags.map(tag => `
        <button type="button" onclick="setTagFilter(${tag.id})" data-tag-id="${tag.id}" 
                class="tag-filter-option w-full px-4 py-2 text-sm text-gray-700 hover:bg-gray-50 transition-colors ${currentTagFilter === tag.id ? 'selected' : ''}">
            <div class="tag-filter-badge" style="background-color: ${tag.color}"></div>
            ${tag.name}
        </button>
    `).join('');
}

// ========================
// INTEGRATED TAG FILTER BAR FUNCTIONS
// ========================

window.selectTagFromBar = function(tagId) {
    // Add selection animation
    const tagBadge = document.querySelector(`[data-tag-id="${tagId}"]`);
    if (tagBadge) {
        tagBadge.classList.add('selecting');
        setTimeout(() => {
            tagBadge.classList.remove('selecting');
        }, 200);
    }
    
    // Update the filter
    currentTagFilter = tagId;
    currentPage = 0;
    
    // Update visual states
    updateTagFilterBarStates();
    
    // Enable/disable reset button
    const resetBtn = document.getElementById('reset-tag-filter-btn');
    if (resetBtn) {
        resetBtn.disabled = (tagId === null);
    }
    
    // Re-render goals and save settings
    renderGoals();
    saveUserSettings();
}

window.resetTagFilter = function() {
    selectTagFromBar(null);
}

function populateTagFilterBar() {
    const container = document.getElementById('tag-filter-grid');
    if (!container) return;
    
    if (tags.length === 0) {
        container.innerHTML = `
            <div class="col-span-full text-center py-4">
                <p class="text-sm text-gray-500 mb-2">No tags available</p>
                <button type="button" onclick="showTagManagementModal();" 
                        class="text-xs px-3 py-1 bg-blue-100 hover:bg-blue-200 text-blue-700 rounded-md transition-colors">
                    Create your first tag
                </button>
            </div>
        `;
        return;
    }
    
    container.innerHTML = tags.map(tag => `
        <button type="button" 
                onclick="selectTagFromBar(${tag.id})" 
                data-tag-id="${tag.id}"
                class="tag-filter-bar-badge ${currentTagFilter === tag.id ? 'active' : ''}"
                style="background-color: ${tag.color}">
            ${tag.name}
        </button>
    `).join('');
}

function updateTagFilterBarStates() {
    // Update all tag badges active states
    document.querySelectorAll('.tag-filter-bar-badge').forEach(badge => {
        const tagId = parseInt(badge.getAttribute('data-tag-id'));
        if (tagId === currentTagFilter) {
            badge.classList.add('active');
        } else {
            badge.classList.remove('active');
        }
    });
}

// Override the old tag filter functions to use the new integrated bar
window.clearTagFilter = function() {
    selectTagFromBar(null);
}

// Update the existing setTagFilter to work with the new system
window.setTagFilter = function(tagId) {
    selectTagFromBar(tagId);
}

// ========================
// TAG UTILITY FUNCTIONS
// ========================

// Render tag badges for a goal
function renderTagBadges(goal, maxVisible = 3) {
    if (!goal.tags || goal.tags.length === 0) {
        return '';
    }
    
    const visibleTags = goal.tags.slice(0, maxVisible);
    const remainingCount = Math.max(0, goal.tags.length - maxVisible);
    
    let badgesHtml = visibleTags.map(tag => `
        <span class="tag-badge" style="background-color: ${tag.color}">
            ${tag.name}
        </span>
    `).join('');
    
    if (remainingCount > 0) {
        badgesHtml += `
            <span class="tag-badge" style="background-color: #6b7280" title="${goal.tags.slice(maxVisible).map(t => t.name).join(', ')}">
                +${remainingCount}
            </span>
        `;
    }
    
    return badgesHtml;
}

// Render modern tag badges for redesigned header
function renderModernTagBadges(goal, maxVisible = 3) {
    if (!goal.tags || goal.tags.length === 0) {
        return '';
    }
    
    const visibleTags = goal.tags.slice(0, maxVisible);
    const remainingCount = Math.max(0, goal.tags.length - maxVisible);
    
    let badgesHtml = visibleTags.map(tag => `
        <span class="modern-tag-badge" style="background-color: ${tag.color}">
            ${tag.name}
        </span>
    `).join('');
    
    if (remainingCount > 0) {
        badgesHtml += `
            <span class="modern-tag-badge modern-tag-more" title="${goal.tags.slice(maxVisible).map(t => t.name).join(', ')}">
                +${remainingCount}
            </span>
        `;
    }
    
    return badgesHtml;
}

// ========================
// TAG SELECTION FUNCTIONS
// ========================

// Note: selectedTagIds is already declared at the top of the file
let editSelectedTagIds = [];

// Render tag selector for goal forms
function renderTagSelector(containerId, selectedIds = []) {
    const container = document.getElementById(containerId);
    if (!container) return;
    
    if (tags.length === 0) {
        container.innerHTML = `
            <p class="text-sm text-gray-500 text-center py-4">
                No tags available. 
                <button type="button" onclick="showTagManagementModal()" class="text-blue-600 hover:text-blue-800 underline">
                    Create your first tag
                </button>
            </p>
        `;
        return;
    }
    
    container.innerHTML = tags.map(tag => {
        const isSelected = selectedIds.includes(tag.id);
        return `
            <div class="tag-option ${isSelected ? 'selected' : ''}" 
                 onclick="toggleTagSelection(${tag.id}, '${containerId}')">
                <div class="tag-option-color" style="background-color: ${tag.color}"></div>
                <div class="tag-option-name">${tag.name}</div>
                ${isSelected ? '<i class="fas fa-check text-blue-600 ml-auto"></i>' : ''}
            </div>
        `;
    }).join('');
}

// Toggle tag selection
window.toggleTagSelection = function(tagId, containerId) {
    console.log('🏷️ Toggling tag selection:', tagId, 'in container:', containerId);
    let targetArray;
    
    if (containerId.includes('create')) {
        targetArray = selectedTagIds;
    } else if (containerId.includes('edit')) {
        targetArray = editSelectedTagIds;
    } else {
        console.warn('Unknown container ID:', containerId);
        return;
    }
    
    const index = targetArray.indexOf(tagId);
    if (index > -1) {
        targetArray.splice(index, 1);
        console.log('📤 Removed tag', tagId, 'from selection');
    } else {
        targetArray.push(tagId);
        console.log('📥 Added tag', tagId, 'to selection');
    }
    
    console.log('🏷️ Updated selection array:', targetArray);
    
    // Re-render to update selection state
    renderTagSelector(containerId, targetArray);
}

// Get selected tags data
function getSelectedTagsData(tagIds) {
    return tags.filter(tag => tagIds.includes(tag.id));
}

// Update goal tags
async function updateGoalTags(goalId, tagIds) {
    try {
        console.log('🚀 Making API call to update goal tags:', { goalId, tagIds });
        const response = await fetch(`/api/goals/${goalId}/tags`, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ tag_ids: tagIds }),
            credentials: 'include'
        });
        
        console.log('📡 API response status:', response.status);
        
        if (!response.ok) {
            const error = await response.json();
            console.error('❌ API error:', error);
            throw new Error(error.error || 'Failed to update goal tags');
        }
        
        const result = await response.json();
        console.log('✅ API success:', result);
        
    } catch (error) {
        console.error('Error updating goal tags:', error);
        throw error;
    }
}

// ========================
// TAG MANAGEMENT FUNCTIONS
// ========================

let currentEditingTagId = null;

// Show tag management modal
window.showTagManagementModal = function() {
    const modal = document.getElementById('tag-management-modal');
    modal.classList.remove('hidden');
    
    // Initialize tag color picker
    initializeTagColorPicker();
    
    // Render existing tags
    renderTagsList();
    
    // Reset form state
    cancelTagForm();
    
    // Add ESC key listener when modal opens
    document.addEventListener('keydown', handleTagModalEscape);
}

// Close tag management modal
window.closeTagManagementModal = function() {
    const modal = document.getElementById('tag-management-modal');
    modal.classList.add('hidden');
    cancelTagForm();
    
    // Remove ESC key listener when modal closes
    document.removeEventListener('keydown', handleTagModalEscape);
}

// Handle ESC key press in tag modal
function handleTagModalEscape(event) {
    if (event.key === 'Escape') {
        const modal = document.getElementById('tag-management-modal');
        if (modal && !modal.classList.contains('hidden')) {
            closeTagManagementModal();
        }
    }
}

// Initialize color picker
function initializeTagColorPicker() {
    const colorPicker = document.getElementById('tag-color-picker');
    if (!colorPicker) return;
    
    colorPicker.innerHTML = '';
    
    tagColors.forEach((color, index) => {
        const colorOption = document.createElement('div');
        colorOption.className = `color-option ${index === 0 ? 'selected' : ''}`;
        colorOption.style.backgroundColor = color.value;
        colorOption.title = color.name;
        colorOption.onclick = () => selectTagColor(color.value, colorOption);
        
        colorPicker.appendChild(colorOption);
    });
    
    // Set default color
    document.getElementById('selected-tag-color').value = tagColors[0].value;
    updateTagPreview();
}

// Select tag color
function selectTagColor(color, element) {
    // Remove selection from all color options
    document.querySelectorAll('.color-option').forEach(opt => {
        opt.classList.remove('selected');
    });
    
    // Select this color
    element.classList.add('selected');
    document.getElementById('selected-tag-color').value = color;
    
    updateTagPreview();
}

// Update tag preview
function updateTagPreview() {
    const nameInput = document.getElementById('tag-name-input');
    const colorInput = document.getElementById('selected-tag-color');
    const preview = document.getElementById('tag-preview');
    
    if (nameInput && colorInput && preview) {
        const name = nameInput.value.trim() || 'Sample Tag';
        const color = colorInput.value;
        
        preview.textContent = name;
        preview.style.backgroundColor = color;
    }
}

// Show tag creation form
window.showTagCreationForm = function() {
    const form = document.getElementById('tag-creation-form');
    const createBtn = document.getElementById('create-tag-btn');
    const formTitle = document.getElementById('tag-form-title');
    const saveBtn = document.getElementById('save-tag-btn');
    
    // Reset form for new tag
    currentEditingTagId = null;
    document.getElementById('tag-name-input').value = '';
    
    // Update UI
    form.classList.remove('hidden');
    createBtn.style.display = 'none';
    formTitle.textContent = 'Create New Tag';
    saveBtn.innerHTML = '<i class="fas fa-check mr-2"></i>Create Tag';
    
    // Reset color selection
    initializeTagColorPicker();
    
    // Focus on name input
    setTimeout(() => {
        document.getElementById('tag-name-input').focus();
    }, 100);
}

// Edit existing tag
window.editTag = function(tagId) {
    const tag = tags.find(t => t.id === tagId);
    if (!tag) return;
    
    const form = document.getElementById('tag-creation-form');
    const createBtn = document.getElementById('create-tag-btn');
    const formTitle = document.getElementById('tag-form-title');
    const saveBtn = document.getElementById('save-tag-btn');
    const nameInput = document.getElementById('tag-name-input');
    const colorInput = document.getElementById('selected-tag-color');
    
    // Set editing mode
    currentEditingTagId = tagId;
    
    // Populate form
    nameInput.value = tag.name;
    colorInput.value = tag.color;
    
    // Update UI
    form.classList.remove('hidden');
    createBtn.style.display = 'none';
    formTitle.textContent = 'Edit Tag';
    saveBtn.innerHTML = '<i class="fas fa-save mr-2"></i>Update Tag';
    
    // Initialize color picker and select current color
    initializeTagColorPicker();
    const colorOption = document.querySelector(`[style*="${tag.color}"]`);
    if (colorOption) {
        selectTagColor(tag.color, colorOption);
    }
    
    updateTagPreview();
    
    // Focus on name input
    setTimeout(() => {
        nameInput.focus();
        nameInput.select();
    }, 100);
}

// Cancel tag form
window.cancelTagForm = function() {
    const form = document.getElementById('tag-creation-form');
    const createBtn = document.getElementById('create-tag-btn');
    
    form.classList.add('hidden');
    createBtn.style.display = 'inline-flex';
    
    // Reset form
    currentEditingTagId = null;
    document.getElementById('tag-name-input').value = '';
    initializeTagColorPicker();
}

// Save tag (create or update)
window.saveTag = async function() {
    const nameInput = document.getElementById('tag-name-input');
    const colorInput = document.getElementById('selected-tag-color');
    const saveBtn = document.getElementById('save-tag-btn');
    
    const name = nameInput.value.trim();
    const color = colorInput.value;
    
    if (!name) {
        authUtils.showErrorMessage('Please enter a tag name');
        nameInput.focus();
        return;
    }
    
    // Check for duplicate names (excluding current tag when editing)
    const existingTag = tags.find(t => t.name.toLowerCase() === name.toLowerCase() && t.id !== currentEditingTagId);
    if (existingTag) {
        authUtils.showErrorMessage('A tag with this name already exists');
        nameInput.focus();
        nameInput.select();
        return;
    }
    
    // Show loading state
    const originalText = saveBtn.innerHTML;
    saveBtn.innerHTML = '<i class="fas fa-spinner fa-spin mr-2"></i>Saving...';
    saveBtn.disabled = true;
    
    try {
        let response;
        
        if (currentEditingTagId) {
            // Update existing tag
            response = await fetch(`/api/tags/${currentEditingTagId}`, {
                method: 'PUT',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ name, color }),
                credentials: 'include'
            });
        } else {
            // Create new tag
            response = await fetch('/api/tags', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ name, color }),
                credentials: 'include'
            });
        }
        
        if (response.ok) {
            const tagData = await response.json();
            
            if (currentEditingTagId) {
                // Update existing tag in array
                const tagIndex = tags.findIndex(t => t.id === currentEditingTagId);
                if (tagIndex !== -1) {
                    tags[tagIndex] = tagData;
                }
                authUtils.showSuccessMessage(`Tag "${name}" updated successfully`);
            } else {
                // Add new tag to array
                tags.push(tagData);
                authUtils.showSuccessMessage(`Tag "${name}" created successfully`);
            }
            
            // Refresh tags list
            renderTagsList();
            // Update tag filter components
            populateTagFilterDropdown();
            populateTagFilterBar();
            
            // Reset form
            cancelTagForm();
            
        } else {
            const error = await response.json();
            authUtils.showErrorMessage(error.error || 'Failed to save tag');
        }
        
    } catch (error) {
        console.error('Error saving tag:', error);
        authUtils.showErrorMessage('Connection error. Please try again');
    } finally {
        // Restore button state
        saveBtn.innerHTML = originalText;
        saveBtn.disabled = false;
    }
}

// Delete tag
window.deleteTag = async function(tagId) {
    const tag = tags.find(t => t.id === tagId);
    if (!tag) return;
    
    if (!confirm(`Are you sure you want to delete the tag "${tag.name}"?\n\nThis will remove it from all goals that use it.`)) {
        return;
    }
    
    try {
        const response = await fetch(`/api/tags/${tagId}`, {
            method: 'DELETE',
            credentials: 'include'
        });
        
        if (response.ok) {
            // Remove from local array
            tags = tags.filter(t => t.id !== tagId);
            
            // Refresh tags list
            renderTagsList();
            // Update tag filter components
            populateTagFilterDropdown();
            populateTagFilterBar();
            
            // Refresh goals to update any that had this tag
            await loadDashboardData();
            
            authUtils.showSuccessMessage(`Tag "${tag.name}" deleted successfully`);
        } else {
            const error = await response.json();
            authUtils.showErrorMessage(error.error || 'Failed to delete tag');
        }
        
    } catch (error) {
        console.error('Error deleting tag:', error);
        authUtils.showErrorMessage('Connection error. Please try again');
    }
}

// Render tags list
function renderTagsList() {
    const tagsList = document.getElementById('tags-list');
    const emptyState = document.getElementById('tags-empty-state');
    
    if (!tagsList || !emptyState) return;
    
    if (tags.length === 0) {
        tagsList.innerHTML = '';
        emptyState.classList.remove('hidden');
        return;
    }
    
    emptyState.classList.add('hidden');
    
    tagsList.innerHTML = tags.map(tag => `
        <div class="tag-item">
            <div class="tag-item-color" style="background-color: ${tag.color}"></div>
            <div class="tag-item-name">${tag.name}</div>
            <div class="tag-item-actions">
                <button onclick="editTag(${tag.id})" class="tag-item-btn edit">
                    <i class="fas fa-edit"></i>
                    Edit
                </button>
                <button onclick="deleteTag(${tag.id})" class="tag-item-btn delete">
                    <i class="fas fa-trash"></i>
                    Delete
                </button>
            </div>
        </div>
    `).join('');
}

// Add event listeners for tag form
document.addEventListener('DOMContentLoaded', function() {
    // Tag name input listeners
    const tagNameInput = document.getElementById('tag-name-input');
    if (tagNameInput) {
        tagNameInput.addEventListener('input', updateTagPreview);
        tagNameInput.addEventListener('keypress', function(e) {
            if (e.key === 'Enter') {
                saveTag();
            }
        });
    }
    
    // Close tag modal when clicking outside
    const tagModal = document.getElementById('tag-management-modal');
    if (tagModal) {
        tagModal.addEventListener('click', function(e) {
            if (e.target === this) {
                closeTagManagementModal();
            }
        });
    }
});

// Load more functionality
window.loadMoreGoals = function() {
    currentPage++;
    renderGoals();
    saveUserSettings();
}

function updateLoadMoreButton() {
    const loadMoreContainer = document.getElementById('load-more-container');
    const totalShown = (currentPage + 1) * goalsPerPage;
    
    if (loadMoreContainer) {
        if (totalShown < filteredGoals.length) {
            loadMoreContainer.classList.remove('hidden');
        } else {
            loadMoreContainer.classList.add('hidden');
        }
    }
}

// Pure CSS hover animations - no JavaScript manipulation needed

// Additional event listeners - set up when DOM is ready
document.addEventListener('DOMContentLoaded', function() {
    // Close modals when clicking outside
    const createModal = document.getElementById('create-goal-modal');
    if (createModal) {
        createModal.addEventListener('click', function(e) {
            if (e.target === this) {
                closeCreateGoalModal();
            }
        });
    }
    
    const editModal = document.getElementById('edit-goal-modal');
    if (editModal) {
        editModal.addEventListener('click', function(e) {
            if (e.target === this) {
                closeEditGoalModal();
            }
        });
    }
});