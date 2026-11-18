/* Copy for the homepage (components/sx). Product facts come from the brief
   for the new Switch app: one chat with Jyoti, ₹0 to post, ₹99 booking fee
   only after a worker accepts, the fare paid straight to the worker,
   full-time ₹1,000 + ₹1,000. Keep this file the single place they live. */

export const WORKER_APP_URL = 'https://play.google.com/store/apps/details?id=com.switchlocally.worker'

export const ROLES = [
  { k: 'Cook', e: '👨‍🍳' },
  { k: 'Kitchen helper', e: '🥘' },
  { k: 'Housekeeping', e: '🧹' },
  { k: 'Waiter', e: '🍽️' },
  { k: 'Utility staff', e: '🧰' },
  { k: 'Picker-packer', e: '📦' },
]

/* The hero chat, one tappable question at a time — the same order Jyoti
   asks in the app. She never fills an answer in for you. */
export const CHAT_STEPS = [
  { key: 'role', q: 'Namaste! Main Jyoti. Kaun sa kaam hai?', tiles: true },
  { key: 'day', q: 'Kis din chahiye?', opts: ['Aaj', 'Kal', 'Parso'] },
  { key: 'time', q: 'Kitne baje se?', opts: ['8 AM', '11 AM', '3 PM', '7 PM'] },
  { key: 'hours', q: 'Kitne ghante ka kaam hai?', opts: ['2 ghante', '4 ghante', '6 ghante', '8 ghante'] },
  { key: 'count', q: 'Kitne log chahiye?', opts: ['1', '2', '3', '4+'] },
  {
    key: 'rate',
    q: 'Hourly rate aap tay kariye. Zyada rate pe worker jaldi milta hai.',
    opts: ['Role minimum', 'Minimum + ₹20', 'Minimum + ₹50'],
  },
  { key: 'gender', q: 'Koi preference?', opts: ['Koi bhi', 'Male', 'Female'] },
]

export const STEPS = [
  {
    n: '01',
    t: 'Talk to Jyoti',
    d: 'Type or speak — Hindi, Hinglish, English or Telugu. She asks role, day, time, hours, how many people, and your address, one small question at a time.',
  },
  {
    n: '02',
    t: 'Set your rate',
    d: 'You choose the hourly rate. Every role has a fixed minimum; paying a little more finds someone faster. Jyoti never decides for you.',
  },
  {
    n: '03',
    t: 'Watch workers get called live',
    d: 'Confirming costs ₹0. Nearby workers get an app ring and a WhatsApp alert — you see who saw it and who said yes, as it happens.',
  },
  {
    n: '04',
    t: 'Pay ₹99 only when someone says yes',
    d: 'When a worker accepts, you pay the ₹99 booking fee. You get the start OTP; they get your address. The fare goes to the worker after the work.',
  },
]

export const LANG_LINES = [
  { l: 'hi', t: 'कल सुबह दो कुक चाहिए' },
  { l: 'en', t: 'Need a waiter tonight in Sector 49' },
  { l: 'hi', t: 'आज फ्री हूँ, काम चाहिए' },
  { l: 'te', t: 'నాకు ఈరోజు పని కావాలి' },
  { l: 'en', t: '2 kitchen helpers, 4 hours, tomorrow 11 AM' },
  { l: 'hl', t: 'Housekeeping ke liye ek didi chahiye' },
  { l: 'te', t: 'రేపు ఉదయం వంటవాడు కావాలి' },
  { l: 'hl', t: 'Picker-packer, Sunday, 8 ghante' },
]

/* Homepage strip: only what a business would say. */
export const LANG_LINES_EMPLOYER = [
  { l: 'hi', t: 'कल सुबह दो कुक चाहिए' },
  { l: 'en', t: 'Need a waiter tonight in Sector 49' },
  { l: 'te', t: 'రేపు ఉదయం వంటవాడు కావాలి' },
  { l: 'en', t: '2 kitchen helpers, 4 hours, tomorrow 11 AM' },
  { l: 'hl', t: 'Housekeeping ke liye ek didi chahiye' },
  { l: 'hi', t: 'आज शाम के लिए एक वेटर चाहिए' },
  { l: 'te', t: 'ఈ రాత్రికి ఇద్దరు వెయిటర్లు కావాలి' },
  { l: 'hl', t: 'Picker-packer, Sunday, 8 ghante' },
]

export const TRUST = [
  { i: 'shield', t: 'Police-verified workers', d: 'Every worker is verified before they can take a job.' },
  { i: 'star', t: 'Ratings after every job', d: 'You rate the worker, the worker rates you. Good work rises.' },
  { i: 'cal', t: 'Start OTP & timer', d: 'The job starts only with your OTP, and the timer runs from there.' },
  { i: 'pin', t: 'Live tracking', d: 'See the worker on the way to your door.' },
  { i: 'book', t: 'Invoice on WhatsApp', d: 'A clean invoice for every booking, sent to your WhatsApp.' },
  { i: 'phone', t: 'A real person to call', d: 'Support on 87968 94500 whenever something isn’t right.' },
]

export const FAQS = [
  {
    q: 'When do I pay?',
    a: 'Posting a shift and confirming it with Jyoti costs ₹0. You pay Switch a ₹99 booking fee only after a worker accepts. The worker’s fare is paid by you directly to the worker after the work — cash or UPI/QR.',
  },
  {
    q: 'Can I set my own rate?',
    a: 'Yes. You set the hourly rate. Each role has a fixed minimum so workers are paid fairly; anything above it helps you find someone faster.',
  },
  {
    q: 'What if the worker doesn’t come?',
    a: 'For hourly shifts, the job only starts with your OTP, and our support team is on 87968 94500 to sort it out. For full-time staff, if the worker doesn’t show up on joining day you don’t pay the second ₹1,000 — and Jyoti finds a replacement.',
  },
  {
    q: 'Does Switch take a cut from the worker?',
    a: 'No. The worker’s full fare goes directly to the worker. Switch earns only the booking fee you pay when a worker accepts.',
  },
  {
    q: 'Which languages does Jyoti speak?',
    a: 'Hindi, Hinglish, English and Telugu. There’s no language screen — the app switches to whatever language you talk in.',
  },
  {
    q: 'What roles can I book?',
    a: 'Cooks, kitchen helpers, housekeeping, waiters, utility staff and picker-packers — for shops, restaurants, PGs, hotels and homes in Gurugram.',
  },
  {
    q: 'How does full-time hiring work?',
    a: 'Tell Jyoti the role, monthly salary (each role has a minimum), duty hours, food/stay and joining date. You pay ₹1,000 when a worker confirms and ₹1,000 when they show up on joining day.',
  },
  {
    q: 'Can I book staff for my home?',
    a: 'Yes. Homes, PGs, shops, restaurants and hotels in Gurugram all book the same way — tell Jyoti the role, day, time and your address, and confirm for ₹0.',
  },
]
