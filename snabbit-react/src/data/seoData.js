/* Meta descriptions are clipped to ~155 characters at a word boundary so
   Google shows them whole. */
function clip(t, max = 155) {
  const x = String(t).replace(/\s+/g, ' ').trim()
  if (x.length <= max) return x
  const cut = x.slice(0, max - 1)
  return cut.slice(0, cut.lastIndexOf(' ')).replace(/[,;:—–-]$/, '').trim() + '…'
}

const SERVICES = [
  {
    id: 'home-cleaning',
    name: 'Home Cleaning',
    plural: 'Home Cleaners',
    verb: 'clean',
    img: '/sw-maid.jpg',
    shortDesc: 'Professional home cleaning services in Gurgaon.',
    longDesc: 'Switch connects you with verified, background-checked home cleaning professionals in Gurgaon. Whether you need a one-time deep clean, regular weekly service, or a quick tidy-up before guests arrive — we have the right worker for you.',
    tasks: [
      'Sweep and mop all floors',
      'Dust furniture, shelves and fixtures',
      'Clean kitchen counters and stovetop',
      'Scrub bathrooms and toilets',
      'Wipe down mirrors and glass surfaces',
      'Vacuum carpets and rugs',
      'Empty trash bins in all rooms',
      'Organize clutter on surfaces',
      'Clean ceiling fans and light fixtures',
      'Mop balconies and utility areas',
    ],
    checklistCategories: [
      { cat: 'Living Room', items: ['Dust all surfaces', 'Vacuum sofa', 'Mop/sweep floors', 'Clean glass doors'] },
      { cat: 'Kitchen', items: ['Wipe counters', 'Clean stovetop', 'Degrease exhaust', 'Mop floor', 'Clean sink'] },
      { cat: 'Bathrooms', items: ['Scrub toilet', 'Clean basin', 'Wipe tiles', 'Mop floor', 'Clean mirror'] },
      { cat: 'Bedrooms', items: ['Dust furniture', 'Change linens', 'Vacuum/sweep', 'Organize surfaces'] },
    ],
    prices: [
      { label: '4 Hours', price: '₹476', desc: 'Quick clean – 1–2 rooms' },
      { label: '8 Hours', price: '₹952', desc: 'Full home – 2–3 BHK' },
      { label: '12 Hours', price: '₹1,428', desc: 'Deep clean – large homes' },
      { label: '2 Days', price: '₹1,904', desc: 'Move-in / move-out clean' },
    ],
    benefits: [
      'Save 3–6 hours every week on household chores',
      'Trained professionals who follow a room-by-room checklist',
      'No agency commissions — pay only for the worker\'s time',
      'Same-day availability for urgent cleaning needs',
      'verified workers you can trust in your home',
      'Flexible slots from 4 hours to multi-day bookings',
      'Consistent quality — same worker each time if you prefer',
    ],
    useCases: [
      'Pre-party or post-party cleaning',
      'Weekly or bi-weekly home maintenance',
      'Move-in or move-out deep cleaning',
      'Post-renovation dust and debris removal',
      'Festival or occasion deep cleaning',
    ],
    faqs: [
      { q: 'How many rooms can a cleaner cover in 4 hours?', a: 'A trained cleaner can cover 1–2 bedrooms plus common areas in 4 hours. For larger homes, book the 8-hour slot.' },
      { q: 'Do I need to provide cleaning supplies?', a: 'Our workers bring basic supplies. For specialty products (specific floor cleaners), we recommend having them available.' },
      { q: 'Can I book a regular weekly cleaner?', a: 'Yes. You can schedule recurring bookings through the Switch app and the same worker will be assigned.' },
      { q: 'Is the cleaner background verified?', a: 'All workers are verified and background checked before they can take bookings.' },
      { q: 'What if I am not satisfied?', a: 'You rate every worker after the job, and good work rises. If something isn’t right, call Switch support on 87968 94500 the same day and we’ll sort it out.' },
      { q: 'Can I request a female cleaner?', a: 'Yes, you can specify your preference while booking and we will do our best to match accordingly.' },
    ],
    areas: ['DLF Phase 1', 'DLF Phase 2', 'DLF Phase 3', 'Sector 14', 'Sector 15', 'Sector 29', 'Sector 45', 'Sector 56', 'Sushant Lok', 'South City', 'Palam Vihar', 'Udyog Vihar'],
    reviews: [
      { name: 'Karishma R.', text: 'Switch is my go-to every week. The cleaner arrives on time and leaves the house spotless. Highly recommend.', rating: 5 },
      { name: 'Neha P.', text: 'Booked for a move-out clean and the team was thorough. Got my full deposit back from the landlord.', rating: 5 },
      { name: 'Ritika M.', text: 'Reasonably priced and very professional. The kitchen and bathrooms were sparkling after the 8-hour session.', rating: 5 },
    ],
  },
  {
    id: 'cook',
    name: 'Cook',
    plural: 'Cooks',
    verb: 'cook',
    img: '/sw-cook.jpg',
    shortDesc: 'Experienced cooks for daily meals, tiffin prep and catering in Gurgaon.',
    longDesc: 'Switch lets you hire skilled cooks in Gurgaon for daily meal preparation, tiffin service, party cooking, and catering support. All cooks are background-verified and experienced in a variety of Indian and regional cuisines.',
    tasks: [
      'Prepare breakfast, lunch and dinner',
      'Make roti, sabzi and dal',
      'Cook rice, biryani and pulao',
      'Prepare snacks and tiffin boxes',
      'Bake and prepare desserts on request',
      'Handle kitchen prep — chopping and marinating',
      'Maintain kitchen hygiene while cooking',
      'Cook for parties and small gatherings',
      'Prepare diet or health meals on request',
      'Make South Indian, North Indian or Mughlai cuisine',
    ],
    checklistCategories: [
      { cat: 'Daily Meals', items: ['Breakfast prep', 'Lunch (2–3 dishes)', 'Dinner (2–3 dishes)', 'Roti / chapati'] },
      { cat: 'Tiffin Service', items: ['Dal + sabzi', 'Rice or roti', 'Salad / raita', 'Pack and label tiffins'] },
      { cat: 'Party Cooking', items: ['Starters', 'Main course', 'Rice / biryani', 'Desserts'] },
      { cat: 'Kitchen Hygiene', items: ['Clean counters after cooking', 'Wash utensils', 'Dispose waste', 'Wipe stovetop'] },
    ],
    prices: [
      { label: '4 Hours', price: '₹1,196', desc: 'Tiffin prep or one meal' },
      { label: '8 Hours', price: '₹2,392', desc: 'Full day meals' },
      { label: '2 Days', price: '₹4,784', desc: 'Weekend cooking' },
      { label: '7 Days', price: '₹9,118', desc: 'Weekly cook' },
    ],
    benefits: [
      'Home-cooked food without the daily effort',
      'Cooks experienced in multiple regional cuisines',
      'Tell Jyoti your kitchen rules — veg-only, no onion-garlic, hygiene needs — in the note',
      'Flexible timings around your schedule',
      'Cost-effective compared to restaurants or cloud kitchens',
      'One booking covers breakfast, lunch and dinner',
      'Diet-specific cooking (low-oil, diabetic, high-protein) on request',
    ],
    useCases: [
      'Working professionals who want home-cooked meals',
      'Families hosting a dinner party or function',
      'Post-surgery or illness recovery diet cooking',
      'New parents who need help with daily meals',
      'Festival cooking — sweets, snacks and special dishes',
    ],
    faqs: [
      { q: 'What cuisines can Switch cooks prepare?', a: 'Our cooks handle North Indian, South Indian, Mughlai, Punjabi, and basic Continental. Mention your preference at booking.' },
      { q: 'Do I need to buy the groceries?', a: 'You provide the groceries. The cook brings their own expertise. You can also ask them to assist with a grocery list.' },
      { q: 'Can I book a cook for a party of 20 people?', a: 'Yes. Mention the headcount when booking and we will match you with a cook experienced in bulk cooking.' },
      { q: 'Is the cook verified?', a: 'All cooks are verified and checked for food handling experience before joining Switch.' },
      { q: 'Can I hire the same cook every day?', a: 'Yes. Through the Switch app you can set up recurring bookings and request the same cook.' },
      { q: 'What if the food quality is not satisfactory?', a: 'Rate the cook after the job and tell Jyoti what you need next time. If something isn’t right, call Switch support on 87968 94500 the same day and we’ll sort it out.' },
    ],
    areas: ['DLF Phase 1', 'DLF Phase 2', 'Sector 29', 'Sector 45', 'Sector 56', 'Sushant Lok', 'Golf Course Road', 'MG Road', 'Palam Vihar', 'Udyog Vihar', 'Cyber City', 'Nirvana Country'],
    reviews: [
      { name: 'Pradnyesh K.', text: 'The cook made the best dal makhani I have had outside a restaurant. Punctual and hygienic.', rating: 5 },
      { name: 'Sameer K.', text: 'Hired for a dinner party of 15 guests. Everything from starters to dessert was perfect.', rating: 5 },
      { name: 'Kirti S.', text: 'Regular 7-day booking. My kids love the food and the cook always checks in about preferences.', rating: 5 },
    ],
  },
  {
    id: 'delivery-worker',
    name: 'Delivery Worker',
    plural: 'Delivery Workers',
    verb: 'deliver',
    img: '/delivery-rider.jpg',
    shortDesc: 'Reliable delivery workers for last-mile delivery, loading and unloading in Gurgaon.',
    longDesc: 'Switch connects you with experienced delivery workers in Gurgaon for last-mile courier runs, loading and unloading, warehouse dispatch support, and store deliveries. Workers are verified and experienced with handling goods carefully.',
    tasks: [
      'Last-mile delivery runs across Gurgaon',
      'Loading and unloading of goods',
      'Parcel sorting and dispatch',
      'Store-to-customer delivery',
      'E-commerce fulfilment support',
      'Intra-city bulk goods transport',
      'Document and envelope courier runs',
      'Furniture and appliance delivery assist',
      'Warehouse picking and packing',
      'Return goods collection',
    ],
    checklistCategories: [
      { cat: 'Dispatch', items: ['Verify consignment list', 'Package integrity check', 'Label all packages', 'Load in delivery order'] },
      { cat: 'Delivery', items: ['Confirm address before leaving', 'Update status per delivery', 'Get recipient signature', 'Photo proof on delivery'] },
      { cat: 'Handling', items: ['Fragile items upright', 'Heavy items at base', 'No stacking on soft goods', 'Secure in vehicle'] },
      { cat: 'Returns', items: ['Collect return items', 'Note reason', 'Re-pack if needed', 'Return to warehouse'] },
    ],
    prices: [
      { label: '4 Hours', price: '₹449', desc: 'Quick local runs' },
      { label: '8 Hours', price: '₹799', desc: 'Full-day delivery' },
      { label: '12 Hours', price: '₹1,099', desc: 'Bulk dispatch day' },
      { label: '7 Days', price: '₹4,499', desc: 'Weekly delivery staff' },
    ],
    benefits: [
      'Reliable workers without long-term employment costs',
      'Available from 4 hours to 7-day contracts',
      'Experienced with fragile, bulk and time-sensitive deliveries',
      'verified — accountable for every delivery',
      'Scalable staffing — add workers during peak demand',
      'Reduce delivery failures with experienced last-mile support',
      'Works with your existing fleet or on foot / bike',
    ],
    useCases: [
      'Seasonal surge — extra delivery staff during sales',
      'New store opening requiring daily delivery coverage',
      'Event materials or gifts distribution',
      'Office pantry restocking and vendor deliveries',
      'E-commerce returns and exchange processing',
    ],
    faqs: [
      { q: 'Do delivery workers have vehicles?', a: 'Workers are available with or without vehicles. Specify at booking — cycle, bike or on-foot for walkable routes.' },
      { q: 'Can I hire for a single busy day?', a: 'Absolutely. The 4-hour or 8-hour plans are ideal for one-off delivery days.' },
      { q: 'What if something goes wrong on a job?', a: 'Every job starts with your OTP and has a timer and a rating. If something isn’t right, call Switch support on 87968 94500 the same day and we’ll sort it out.' },
      { q: 'Can I hire multiple workers at once?', a: 'Yes. Book individually or contact Switch at hello@switchlocally.com for bulk workforce requests.' },
      { q: 'Do they handle fragile or high-value items?', a: 'Yes. Mention fragile handling at booking and we assign workers with relevant experience.' },
      { q: 'Can delivery workers also help with loading/unloading?', a: 'Yes. Loading and unloading support is included in the standard booking.' },
    ],
    areas: ['Udyog Vihar', 'Cyber City', 'MG Road', 'Sohna Road', 'IMT Manesar', 'Palam Vihar', 'Sector 29', 'DLF Phase 1', 'Golf Course Road', 'Sector 45', 'Sector 56', 'Manesar'],
    reviews: [
      { name: 'Sameer K.', text: 'Hired 3 delivery workers for our Diwali sale. Zero failed deliveries. Will book again.', rating: 5 },
      { name: 'Pradnyesh K.', text: 'Needed a loader for our office move. Efficient, careful and no damage to equipment.', rating: 5 },
      { name: 'Kirti S.', text: 'Reliable same-day bookings for our small business deliveries. Switch is a lifesaver.', rating: 5 },
    ],
  },
  {
    id: 'nanny',
    name: 'Nanny',
    plural: 'Nannies',
    verb: 'care',
    img: '/sw-caretaker.jpg',
    shortDesc: 'Trusted nannies and babysitters for childcare, school pickup and homework help in Gurgaon.',
    longDesc: 'Switch connects you with experienced, background-verified nannies and babysitters in Gurgaon for full-day childcare, after-school supervision, school pickup and drop, and homework assistance. All nannies are verified and child-safety trained.',
    tasks: [
      'Full-day childcare for infants and toddlers',
      'School pickup and safe drop at home',
      'After-school supervision and activity time',
      'Homework help and reading practice',
      'Meal prep and feeding young children',
      'Bathing, dressing and nap routines',
      'Playing and engaging activities',
      'Light housekeeping related to child areas',
      'Night nanny support for newborns',
      'Accompanying parents on outings with children',
    ],
    checklistCategories: [
      { cat: 'Daily Routine', items: ['Morning routine assistance', 'Meal time supervision', 'Nap schedule', 'Evening activity'] },
      { cat: 'Safety', items: ['Childproof environment check', 'First aid awareness', 'Emergency contact ready', 'No unsupervised screen time'] },
      { cat: 'Learning', items: ['Homework assistance', 'Reading time', 'Craft / drawing', 'Educational play'] },
      { cat: 'Hygiene', items: ['Bathing assistance', 'Teeth brushing', 'Hand wash before meals', 'Changing diapers / clothes'] },
    ],
    prices: [
      { label: '4 Hours', price: '₹549', desc: 'After-school care' },
      { label: '8 Hours', price: '₹999', desc: 'Full workday care' },
      { label: '2 Days', price: '₹1,799', desc: 'Weekend childcare' },
      { label: '7 Days', price: '₹5,999', desc: 'Weekly nanny' },
    ],
    benefits: [
      'Experienced with infants, toddlers and school-age children',
      'verified and police-checked for child safety',
      'Flexible hours — match your work schedule exactly',
      'Consistent childcare from the same trusted nanny',
      'Homework help so children stay academically supported',
      'Parents receive updates through the Switch app',
      'Trained in basic child first aid',
    ],
    useCases: [
      'Working parents who need reliable daily childcare',
      'Parents travelling for work needing overnight nanny',
      'School pickup and homework supervision',
      'Newborn care support for new parents',
      'Childcare during family events or ceremonies',
    ],
    faqs: [
      { q: 'Are nannies background verified?', a: 'Yes. All Switch nannies are verified and go through an enhanced check for childcare roles.' },
      { q: 'Can I book the same nanny every day?', a: 'Yes. Set up recurring bookings through the app and request your preferred nanny.' },
      { q: 'Are nannies trained in first aid?', a: 'All Switch nannies complete a basic child safety and first aid orientation before onboarding.' },
      { q: 'Can a nanny handle a newborn?', a: 'Yes. Mention at booking that you need infant care and we assign a nanny with newborn experience.' },
      { q: 'What age children can they care for?', a: 'Switch nannies work with newborns (0 months) through school-age children (12 years).' },
      { q: 'Can I get a nanny for just 4 hours after school?', a: 'Absolutely. The 4-hour slot is perfect for after-school pickup and care until you return from work.' },
    ],
    areas: ['DLF Phase 1', 'DLF Phase 2', 'DLF Phase 3', 'Sector 29', 'Sector 45', 'Sushant Lok', 'Golf Course Road', 'South City', 'Palam Vihar', 'Sector 56', 'Nirvana Country', 'Sector 14'],
    reviews: [
      { name: 'Rabia A.', text: 'Got a nanny for 2 weeks. She was wonderful with my kids — completely reliable and trusted.', rating: 5 },
      { name: 'Neha P.', text: 'My daughter loves her nanny from Switch. School pickup, homework, evening routine — all handled.', rating: 5 },
      { name: 'Kirti S.', text: 'As a working mom, Switch has been a lifesaver. Professional, caring and punctual nanny every day.', rating: 5 },
    ],
  },
  {
    id: 'security-guard',
    name: 'Security Guard',
    plural: 'Security Guards',
    verb: 'secure',
    img: '/sw-security-guard.jpg',
    shortDesc: 'Trained security guards for residential, commercial and event security in Gurgaon.',
    longDesc: 'Switch connects you with trained, background-verified security guards in Gurgaon for gate duty, premises security, night patrol, and event security. All guards hold a security licence, are verified, and are trained in access control and emergency response.',
    tasks: [
      'Gate entry and exit management',
      'Visitor log and identity verification',
      'Night patrol of premises',
      'CCTV monitoring assistance',
      'Vehicle parking management',
      'Emergency response and escalation',
      'Package and courier receive / dispatch',
      'Intrusion detection and reporting',
      'Event crowd management',
      'Office and commercial premises security',
    ],
    checklistCategories: [
      { cat: 'Entry Control', items: ['Verify visitor ID', 'Maintain visitor log', 'Issue entry pass', 'Escort to destination'] },
      { cat: 'Patrol', items: ['Perimeter walk every 2 hours', 'Check all exit points', 'Verify lock status', 'Report anomalies'] },
      { cat: 'Emergency', items: ['Emergency contacts posted', 'Know evacuation routes', 'First responder basics', 'Incident report template'] },
      { cat: 'Documentation', items: ['Shift handover log', 'Visitor register', 'Incident log', 'Vehicle entry/exit record'] },
    ],
    prices: [
      { label: '12 Hours', price: '₹2,148', desc: 'Day or night shift' },
      { label: '2 Days', price: '₹2,864', desc: 'Event security' },
      { label: '7 Days', price: '₹6,808', desc: 'Weekly guard' },
      { label: 'Custom', price: 'Quote', desc: 'Long-term deployment' },
    ],
    benefits: [
      'Licensed and verified security professionals',
      'Trained in access control, crowd management and emergency response',
      'Available for day, night or 24-hour shifts',
      'Scalable — book 1 guard or a full team for events',
      'Uniformed and professional appearance',
      'Reduces insurance and liability risks for your premises',
      'On-time shift changes — no coverage gaps',
    ],
    useCases: [
      'Residential society gate security for a week',
      'Wedding or event crowd and entry management',
      'Office or warehouse overnight security',
      'Construction site security during off-hours',
      'Festival or public event security deployment',
    ],
    faqs: [
      { q: 'Do guards have a security licence?', a: 'Yes. All Switch guards hold a PSARA licence or equivalent and are verified before onboarding.' },
      { q: 'Are guards available for night shifts?', a: 'Yes. Both day (7 AM – 7 PM) and night (7 PM – 7 AM) shifts are available.' },
      { q: 'Can I hire for a single event?', a: 'Absolutely. The 2-day plan is ideal for weddings, functions and one-time events.' },
      { q: 'Do guards carry weapons?', a: 'Standard guards are unarmed. For armed security, contact us at hello@switchlocally.com for a custom deployment.' },
      { q: 'What happens at shift handover?', a: 'Guards maintain a detailed shift log and provide a handover briefing to the next guard or client.' },
      { q: 'Can I get a female security guard?', a: 'Yes. Female guards are available for women-only premises and events. Mention at booking.' },
    ],
    areas: ['DLF Phase 1', 'DLF Phase 2', 'Cyber City', 'Udyog Vihar', 'IMT Manesar', 'Sector 29', 'Sohna Road', 'Golf Course Road', 'Palam Vihar', 'South City', 'Sector 56', 'Manesar'],
    reviews: [
      { name: 'Pradnyesh K.', text: 'Needed 2 guards for our office for a week. Professional, punctual and thorough.', rating: 5 },
      { name: 'Sameer K.', text: 'Hired event security for our store launch. Entry was smooth and organized throughout.', rating: 5 },
      { name: 'Ridhi S.', text: 'Night patrol guard for our society. Detailed shift logs every morning. Very reliable.', rating: 5 },
    ],
  },
  {
    id: 'store-helper',
    name: 'Store Helper',
    plural: 'Store Helpers',
    verb: 'assist',
    img: '/sw-general-helper.jpg',
    shortDesc: 'Reliable store helpers for stacking, billing and customer floor support in Gurgaon.',
    longDesc: 'Switch connects you with experienced store helpers in Gurgaon for shelf stacking, inventory management, billing counter support, and customer floor assistance. All workers are verified and trained for retail environments.',
    tasks: [
      'Shelf stacking and product arrangement',
      'Billing counter assistance',
      'Customer floor support and guidance',
      'Inventory counting and stock check',
      'Unloading delivery stock',
      'Price tagging and label placement',
      'Store opening and closing duties',
      'Display setup and visual merchandising support',
      'Cash and carry packaging assistance',
      'Daily sweep and store hygiene maintenance',
    ],
    checklistCategories: [
      { cat: 'Stocking', items: ['Unbox new stock', 'Shelve by category', 'Check expiry dates', 'Face products forward'] },
      { cat: 'Customer Support', items: ['Greet customers', 'Guide to product location', 'Assist with heavy items', 'Handle basic queries'] },
      { cat: 'Billing Area', items: ['Pack items', 'Hand bags to customers', 'Manage queue flow', 'Keep counter tidy'] },
      { cat: 'Store Upkeep', items: ['Sweep aisles', 'Remove empty cartons', 'Wipe shelves', 'Maintain trial room'] },
    ],
    prices: [
      { label: '8 Hours', price: '₹1,432', desc: 'Full-day store support' },
      { label: '12 Hours', price: '₹2,148', desc: 'Extended shift' },
      { label: '2 Days', price: '₹2,864', desc: 'Weekend or sale event' },
      { label: '7 Days', price: '₹6,537', desc: 'Weekly store staffing' },
    ],
    benefits: [
      'Reliable cover during peak hours and festive sales',
      'No long-term employment commitment required',
      'Workers experienced in retail floor operations',
      'Scale up staff quickly during Diwali or year-end sales',
      'verified — accountable and trustworthy',
      'Reduce checkout wait times with extra billing support',
      'Flexible durations — book for a day or a full week',
    ],
    useCases: [
      'Festive or sale period staffing surge',
      'New store launch requiring extra floor hands',
      'Staff shortage cover at short notice',
      'Inventory restock after delivery',
      'Weekend crowd management support',
    ],
    faqs: [
      { q: 'Can I book a store helper for a single day?', a: 'Yes. The 8-hour plan is ideal for a single shift. Book from the Switch app and confirm same day.' },
      { q: 'Are workers experienced in retail?', a: 'Yes. Store helpers on Switch have prior retail or inventory experience verified during onboarding.' },
      { q: 'Can I hire multiple helpers at once?', a: 'Yes. Book individually or contact hello@switchlocally.com for bulk staffing requests during sales.' },
      { q: 'Are workers background verified?', a: 'Yes. All workers are verified and background checked.' },
      { q: 'Can helpers assist at a billing counter?', a: 'Yes. They can pack, bag, and assist at the counter — mention this requirement at booking.' },
      { q: 'What if the worker doesn\'t show up?', a: 'The job only starts with your OTP, so you never pay a fare for a no-show. Call support on 87968 94500 and Jyoti will alert other nearby workers. For full-time staff, you don\'t pay the second ₹1,000 if they don\'t join, and Jyoti finds a replacement.' },
    ],
    areas: ['MG Road', 'Sector 29', 'Udyog Vihar', 'DLF Phase 1', 'DLF Phase 2', 'Sohna Road', 'Golf Course Road', 'Sector 45', 'Palam Vihar', 'Cyber City', 'Sector 14', 'South City'],
    reviews: [
      { name: 'Sameer K.', text: 'Our store needed part-time help during Diwali. Switch sent 3 experienced hands within hours.', rating: 5 },
      { name: 'Kirti S.', text: 'Hired a store helper for a new product launch. Handled stocking and billing counter perfectly.', rating: 5 },
      { name: 'Pradnyesh K.', text: 'Reliable, punctual and good with customers. Will keep using Switch for our store.', rating: 5 },
    ],
  },
  {
    id: 'factory-warehouse',
    name: 'Factory / Warehouse',
    plural: 'Factory & Warehouse Workers',
    verb: 'operate',
    img: '/sw-factory-helper.jpg',
    shortDesc: 'Trained factory and warehouse workers for sorting, packing and assembly line support in Gurgaon.',
    longDesc: 'Switch connects you with experienced factory and warehouse workers in Gurgaon for sorting, packing, assembly line operations, inventory management, and loading and unloading. All workers are verified and familiar with industrial safety protocols.',
    tasks: [
      'Sorting and segregation of goods',
      'Packing and labelling products',
      'Assembly line station support',
      'Loading and unloading trucks',
      'Inventory counting and stock audits',
      'Bin and rack organisation',
      'Barcode scanning and data entry',
      'Quality check and reject segregation',
      'Wrapping and palletising goods',
      'Housekeeping of warehouse floor',
    ],
    checklistCategories: [
      { cat: 'Incoming Goods', items: ['Verify delivery challan', 'Count and check items', 'Mark damaged goods', 'Stock into assigned bin'] },
      { cat: 'Packing', items: ['Pack per SKU instructions', 'Label with product info', 'Seal and tape securely', 'Stack on pallet'] },
      { cat: 'Dispatch', items: ['Pick items per order', 'Pack and weigh', 'Generate shipping label', 'Load onto vehicle'] },
      { cat: 'Safety', items: ['Wear PPE as required', 'Keep aisles clear', 'Report spills immediately', 'No unauthorised zone entry'] },
    ],
    prices: [
      { label: '8 Hours', price: '₹1,144', desc: 'Single shift' },
      { label: '12 Hours', price: '₹1,716', desc: 'Extended production shift' },
      { label: '2 Days', price: '₹2,288', desc: 'Short-term project' },
      { label: '7 Days', price: '₹6,291', desc: 'Weekly workforce' },
    ],
    benefits: [
      'Scale up workforce quickly for peak production seasons',
      'No permanent headcount — hire flexibly by the day',
      'Workers familiar with factory safety and protocol',
      'verified and accountable for goods handling',
      'Reduce overtime by adding shift support workers',
      'Experienced with packing, assembly and sorting operations',
      'Available for 8-hour, 12-hour or multi-day shifts',
    ],
    useCases: [
      'Peak order season requiring extra packing staff',
      'New product launch requiring assembly line support',
      'Inventory audit needing additional counting staff',
      'Truck arrival requiring fast loading and unloading crew',
      'Factory maintenance period requiring warehouse staff cover',
    ],
    faqs: [
      { q: 'Can factory workers handle food or pharmaceutical products?', a: 'Yes. Mention the product type at booking and we assign workers with relevant handling experience.' },
      { q: 'Are workers familiar with safety protocols?', a: 'Yes. All Switch factory workers complete a basic industrial safety orientation before onboarding.' },
      { q: 'Can I hire a team of 5 or more workers?', a: 'Yes. Contact hello@switchlocally.com for bulk workforce requests of 5 or more workers.' },
      { q: 'Are workers available for night shifts?', a: 'Yes. Both day and night shift workers are available. Specify your shift timing at booking.' },
      { q: 'Do workers bring their own equipment?', a: 'Workers bring themselves. PPE and tools should be provided by the facility as per safety standards.' },
      { q: 'How quickly can I get workers on short notice?', a: 'Jyoti alerts nearby workers the moment you confirm, and you see who said yes live. A slightly higher hourly rate usually gets a yes sooner.' },
    ],
    areas: ['IMT Manesar', 'Udyog Vihar', 'Sector 37', 'Sohna Road', 'DLF Phase 1', 'Pataudi Road', 'Sector 29', 'Sector 56', 'Cyber City', 'Manesar', 'Palam Vihar', 'NH-48'],
    reviews: [
      { name: 'Pradnyesh K.', text: 'Needed 4 warehouse workers urgently. Got verified staff same-day. Absolute lifesaver for our business.', rating: 5 },
      { name: 'Sameer K.', text: 'Hired 3 packers for our festive season rush. Efficient, reliable and no damage to goods.', rating: 5 },
      { name: 'Ridhi S.', text: 'Assembly line support during a product launch. Workers were trained and quick to adapt.', rating: 5 },
    ],
  },
  {
    id: 'kitchen-helper',
    name: 'Kitchen Helper',
    plural: 'Kitchen Helpers',
    verb: 'help in the kitchen',
    img: '/sw-kitchen-helper.jpg',
    shortDesc: 'Kitchen helpers for restaurants, cafés, cloud kitchens, PGs and homes in Gurgaon.',
    longDesc: 'A kitchen helper keeps your kitchen moving so your cooks can cook — prep, washing up, cleaning and plating during the rush. Book one for a lunch or dinner shift, a busy weekend, or full-time, by telling Jyoti what your kitchen needs.',
    tasks: [
      'Wash, peel and chop vegetables',
      'Prep and portion ingredients before service',
      'Wash utensils, pots and containers',
      'Keep counters, floors and stations clean',
      'Help plate and pack orders during the rush',
      'Unload and store deliveries',
      'Take out waste and keep bins clean',
      'Refill sauces, masalas and garnish stations',
    ],
    checklistCategories: [
      { cat: 'Before service', items: ['Vegetable prep', 'Mise en place', 'Clean stations'] },
      { cat: 'During service', items: ['Wash-up', 'Plating & packing help', 'Refill stations'] },
      { cat: 'After service', items: ['Deep clean counters', 'Mop floors', 'Waste out'] },
    ],
    prices: [],
    benefits: [
      'Cover a lunch or dinner rush without hiring full-time',
      'You set the hourly rate; each role has a fixed minimum',
      'Nearby helpers are alerted first, so they reach on time',
      'Start OTP and a timer on every shift',
      'Rate each helper after the job — good ones rise',
      'Need someone permanent? Hire full-time with the same chat',
    ],
    useCases: [
      'A weekend rush at a restaurant or café',
      'Cloud kitchens with an evening order spike',
      'PG and hostel kitchens that need daily help',
      'Weddings and parties with extra cooking',
      'Covering a staff member on leave',
    ],
    faqs: [
      { q: 'What does a kitchen helper do?', a: 'Prep, washing up, cleaning and helping during service — chopping vegetables, washing utensils, keeping stations clean and helping plate or pack orders. Tell Jyoti anything specific in the note for the worker.' },
      { q: 'Can I book a kitchen helper for just one shift?', a: 'Yes. Book for a few hours — a lunch or dinner shift — or longer. Posting is ₹0, and you pay the ₹99 booking fee only when a helper accepts.' },
      { q: 'How much does a kitchen helper cost?', a: 'You set the hourly rate (each role has a fixed minimum) and pay the helper directly after the work, cash or UPI. Switch charges only the ₹99 booking fee after someone accepts.' },
      { q: 'Can I hire a full-time kitchen helper?', a: 'Yes. Tell Jyoti the monthly salary, duty hours, food/stay and joining date. The fee is ₹1,000 when a worker confirms and ₹1,000 when they join.' },
      { q: 'Are kitchen helpers verified?', a: 'Yes, every worker is verified before they can take a job, and each shift starts with your OTP.' },
    ],
    areas: ['Cyber Hub', 'Sector 29', 'Golf Course Road', 'Sohna Road', 'Udyog Vihar', 'DLF Phase 4', 'Sector 14', 'MG Road', 'Sushant Lok', 'Sector 56'],
    reviews: [],
  },
  {
    id: 'waiter',
    name: 'Waiter',
    plural: 'Waiters',
    verb: 'serve',
    img: '/sw-waiter.jpg',
    shortDesc: 'Waiters for restaurants, cafés, banquets, parties and events in Gurgaon.',
    longDesc: 'Book waiters for a busy weekend service, a banquet or a house party. Tell Jyoti how many you need, the time and the dress code, and she alerts verified waiters nearby — you see who says yes, live.',
    tasks: [
      'Greet guests and seat them',
      'Take orders and serve food and drinks',
      'Lay and clear tables',
      'Serve at buffets, counters and live stations',
      'Pass starters and drinks at parties',
      'Keep the floor and service area tidy',
      'Help with setup and wind-down after events',
    ],
    checklistCategories: [
      { cat: 'Restaurant service', items: ['Seat guests', 'Take orders', 'Serve & clear'] },
      { cat: 'Events & parties', items: ['Pass starters', 'Buffet service', 'Drinks service'] },
      { cat: 'Before & after', items: ['Table setup', 'Clear down', 'Tidy the floor'] },
    ],
    prices: [],
    benefits: [
      'Extra hands for a weekend rush or a one-night event',
      'Book 1 waiter or a full team in one chat',
      'You set the hourly rate; pay a little more for a faster yes',
      'Nearest waiters are alerted first',
      'Start OTP and live tracking on every booking',
      '₹0 to post — ₹99 only after a waiter accepts',
    ],
    useCases: [
      'Friday and Saturday dinner service',
      'Banquets, weddings and receptions',
      'House parties and family functions',
      'Corporate lunches and office events',
      'Café launches and promotions',
    ],
    faqs: [
      { q: 'Can I book several waiters for an event?', a: 'Yes. Tell Jyoti how many people you need — she alerts nearby waiters and you see each yes come in live.' },
      { q: 'Can I ask for a dress code?', a: 'Yes. Add it in the note for the worker — for example black shirt and trousers — when you book.' },
      { q: 'How much does a waiter cost per hour?', a: 'You set the hourly rate (each role has a fixed minimum). The fare goes to the waiter directly after the work; Switch charges only the ₹99 booking fee after someone accepts.' },
      { q: 'Can I book a waiter for tonight?', a: 'Yes. Tell Jyoti it is for today and the time. A slightly higher rate usually gets a yes sooner.' },
      { q: 'Are the waiters verified?', a: 'Yes, every worker is verified before they can take a job, and the shift starts only with your OTP.' },
    ],
    areas: ['Cyber Hub', 'Golf Course Road', 'Sector 29', 'MG Road', 'DLF Phase 1', 'DLF Phase 5', 'Sohna Road', 'Sushant Lok', 'Sector 45', 'Udyog Vihar'],
    reviews: [],
  },
  {
    id: 'utility-staff',
    name: 'Utility Staff',
    plural: 'Utility Staff',
    verb: 'help',
    img: '/sw-general-helper.jpg',
    shortDesc: 'Utility staff for shops, offices, PGs, hotels and homes in Gurgaon.',
    longDesc: 'Utility staff handle the everyday jobs that keep a place running — cleaning, shifting, loading, errands and general help. Book someone for a few hours or full-time by telling Jyoti the work, time and address.',
    tasks: [
      'General cleaning of floors, stairs and common areas',
      'Shift furniture, stock and boxes',
      'Load and unload deliveries',
      'Run local errands and pickups',
      'Help with setup for events and meetings',
      'Water plants and tidy outdoor areas',
      'Assist in the pantry or store room',
    ],
    checklistCategories: [
      { cat: 'Cleaning', items: ['Floors & stairs', 'Common areas', 'Waste out'] },
      { cat: 'Moving & loading', items: ['Shift furniture', 'Load/unload stock', 'Arrange store room'] },
      { cat: 'General help', items: ['Errands', 'Event setup', 'Pantry help'] },
    ],
    prices: [],
    benefits: [
      'One booking for the odd jobs nobody else has time for',
      'Hourly for a one-off job, or full-time for every day',
      'You set the hourly rate; each role has a fixed minimum',
      'Nearby workers alerted first — app ring plus WhatsApp',
      'Start OTP, timer and rating on every job',
      '₹0 to post, ₹99 only after someone accepts',
    ],
    useCases: [
      'Shops and stores shifting stock or cleaning up',
      'Offices needing daily cleaning and errands',
      'PGs and hotels with general upkeep',
      'Homes moving furniture or cleaning after a party',
      'Event setup and wind-down',
    ],
    faqs: [
      { q: 'What can utility staff help with?', a: 'Cleaning, shifting and loading, errands and general help. Describe the job to Jyoti and add anything specific in the note for the worker.' },
      { q: 'Can I hire utility staff for just a few hours?', a: 'Yes. Book hourly for a one-off job. Posting is ₹0 and you pay the ₹99 booking fee only when someone accepts.' },
      { q: 'Can I hire full-time utility staff?', a: 'Yes. Tell Jyoti the monthly salary, duty hours, food/stay and joining date. You pay ₹1,000 when a worker confirms and ₹1,000 when they join.' },
      { q: 'How do I pay the worker?', a: 'Directly, after the work — cash or UPI. Switch takes no cut of the fare.' },
    ],
    areas: ['Udyog Vihar', 'Sector 14', 'Sector 29', 'MG Road', 'Sohna Road', 'Palam Vihar', 'DLF Phase 3', 'Sushant Lok', 'Sector 49', 'Golf Course Road'],
    reviews: [],
  },
  {
    id: 'picker-packer',
    name: 'Picker & Packer',
    plural: 'Pickers & Packers',
    verb: 'pick and pack',
    img: '/sw-picker-packer.jpg',
    shortDesc: 'Pickers and packers for warehouses, dark stores and e-commerce sellers in Gurgaon.',
    longDesc: 'Pickers and packers keep orders flowing in warehouses, dark stores and seller godowns — picking from racks, packing, labelling and sorting for dispatch. Book a few for a sale-day spike or a regular shift through one chat with Jyoti.',
    tasks: [
      'Pick items from racks against an order list',
      'Pack, seal and label orders',
      'Sort parcels for dispatch',
      'Count and check incoming stock',
      'Stack and arrange shelves',
      'Load and unload cartons',
      'Keep the packing area clean and organised',
    ],
    checklistCategories: [
      { cat: 'Picking', items: ['Pick to list', 'Check SKU & count', 'Stage for packing'] },
      { cat: 'Packing', items: ['Pack & seal', 'Label', 'Sort for dispatch'] },
      { cat: 'Stock', items: ['Inward check', 'Shelving', 'Cartons in/out'] },
    ],
    prices: [],
    benefits: [
      'Scale up for sale days without permanent hiring',
      'Book 1 or a full shift team in one chat',
      'You set the hourly rate; pay more for a faster yes',
      'Workers near your warehouse are alerted first',
      'Start OTP and timer for clean attendance',
      '₹0 to post, ₹99 only after a worker accepts',
    ],
    useCases: [
      'Sale-day and festive order spikes',
      'Dark stores and quick-commerce hubs',
      'E-commerce sellers packing from a godown',
      'Inventory counts and stock shifts',
      'Covering absent staff on a shift',
    ],
    faqs: [
      { q: 'Can I book pickers and packers for a 12-hour shift?', a: 'Yes. Tell Jyoti the hours and how many people you need. Each worker gets an app ring and a WhatsApp alert.' },
      { q: 'How many pickers can I book at once?', a: 'As many as you need — set the headcount and watch each yes come in live.' },
      { q: 'What does it cost?', a: 'You set the hourly rate (each role has a fixed minimum) and pay each worker directly after the shift. Switch charges only the ₹99 booking fee after a worker accepts.' },
      { q: 'Do workers check in at the warehouse?', a: 'Yes. The shift starts only with your start OTP, and a timer runs from there.' },
    ],
    areas: ['Udyog Vihar', 'Sector 85', 'Sector 37', 'IMT Manesar', 'Sohna Road', 'Sector 18', 'Palam Vihar', 'Sector 10', 'Sector 49', 'Bilaspur'],
    reviews: [],
  },
]

// ─── PAGE GENERATORS ─────────────────────────────

function makeLandingPage(s) {
  return {
    slug: `${s.id}-gurgaon`,
    type: 'landing',
    service: s.name,
    serviceId: s.id,
    serviceImg: s.img,
    title: `${s.name} in Gurgaon — Book in Minutes | Switch`,
    description: clip(`Book verified ${s.plural.toLowerCase()} in Gurgaon by chatting with Jyoti — Hindi or English. ₹0 to post, ₹99 only when a worker says yes. ${s.shortDesc}`),
    h1: `${s.name} in Gurgaon`,
    intro: `Need reliable ${s.plural.toLowerCase()} in Gurgaon? Just tell Jyoti the day, time and hours — in Hindi or English. She alerts verified ${s.plural.toLowerCase()} near you, and you pay the ₹99 booking fee only when one says yes.`,
    tasks: s.tasks,
    prices: s.prices,
    faqs: s.faqs,
    reviews: s.reviews,
    benefits: s.benefits,
    areas: s.areas,
    longDesc: s.longDesc,
  }
}

function makePricingPage(s) {
  return {
    slug: `${s.id}-cost-gurgaon`,
    type: 'pricing',
    service: s.name,
    serviceId: s.id,
    serviceImg: s.img,
    title: `${s.name} Cost in Gurgaon (2026) | Switch`,
    description: clip(`What ${s.plural.toLowerCase()} cost in Gurgaon on Switch: ₹0 to post, you set the hourly rate, ₹99 booking fee only after a worker accepts. No commission on the fare.`),
    h1: `${s.name} Cost in Gurgaon — Pricing & Rates`,
    intro: `Wondering how much a ${s.name.toLowerCase()} costs in Gurgaon? Switch offers transparent, all-in pricing with no hidden fees. Pay against a clear invoice, with no hidden charges.`,
    prices: s.prices,
    faqs: s.faqs.slice(0, 4),
    pricingNotes: [
      'All rates include worker time and standard tools',
      'Materials and parts are billed at cost separately',
      'No booking or platform fees',
      '₹0 to post; ₹99 booking fee only after a worker accepts; the fare goes to the worker directly',
      'Cancel or reschedule free up to 2 hours before start',
    ],
    tasks: s.tasks.slice(0, 5),
    areas: s.areas,
  }
}

function makeHowToHirePage(s) {
  return {
    slug: `hire-${s.id}-gurgaon`,
    type: 'how-to-hire',
    service: s.name,
    serviceId: s.id,
    serviceImg: s.img,
    title: `How to Hire a ${s.name} in Gurgaon | Switch`,
    description: clip(`How to hire verified ${s.plural.toLowerCase()} in Gurgaon: tell Jyoti the shift, set your rate, watch nearby workers respond live, pay ₹99 only after a yes.`),
    h1: `How to Hire a ${s.name} in Gurgaon`,
    intro: `Hiring a ${s.name.toLowerCase()} in Gurgaon used to mean calling agencies, dealing with middlemen and overpaying. Switch changes all that. Here is how to get a verified professional in three simple steps.`,
    steps: [
      { n: '1', title: 'Tell Jyoti what you need', desc: `Open the Switch app and say or type it — “${s.name.toLowerCase()} kal 11 baje, 4 ghante”. Jyoti asks the rest one small question at a time.` },
      { n: '2', title: 'Set your rate and confirm for ₹0', desc: 'Choose the hourly rate (each role has a fixed minimum), add your Gurgaon address and confirm — posting is free. Nearby workers get an app ring and WhatsApp alert.' },
      { n: '3', title: 'Worker arrives — work gets done', desc: `Your verified ${s.name.toLowerCase()} arrives and starts with your OTP. Pay their fare directly after the work — cash or UPI — and get the invoice on WhatsApp.` },
    ],
    tips: [
      `Post a few hours ahead and set a slightly higher rate to get a yes faster`,
      `Describe your specific requirement in the notes field`,
      `Watch who saw your shift and who said yes — you pay the ₹99 booking fee only then`,
      `Keep your phone accessible — the worker will call if they need directions`,
      `Have materials or supplies ready before the worker arrives`,
    ],
    faqs: s.faqs,
    areas: s.areas,
    tasks: s.tasks.slice(0, 6),
  }
}

function makeBenefitsPage(s) {
  return {
    slug: `${s.id}-benefits-gurgaon`,
    type: 'benefits',
    service: s.name,
    serviceId: s.id,
    serviceImg: s.img,
    title: `Benefits of Hiring a ${s.name} in Gurgaon from Switch`,
    description: `Discover the top benefits of booking a verified ${s.name.toLowerCase()} in Gurgaon through Switch. Save time, get quality work, and pay transparent, fixed rates.`,
    h1: `Benefits of Hiring a ${s.name} in Gurgaon`,
    intro: `Hiring a ${s.name.toLowerCase()} through Switch in Gurgaon means more than just getting the job done — it means getting it done right, on time, and at a fair price. Here is why thousands of Gurgaon residents choose Switch.`,
    benefits: s.benefits,
    useCases: s.useCases,
    faqs: s.faqs.slice(0, 4),
    tasks: s.tasks,
    areas: s.areas.slice(0, 6),
  }
}

function makeChecklistPage(s) {
  return {
    slug: `${s.id}-checklist-gurgaon`,
    type: 'checklist',
    service: s.name,
    serviceId: s.id,
    serviceImg: s.img,
    title: `${s.name} Checklist Gurgaon – What's Included | Switch`,
    description: `Full ${s.name.toLowerCase()} checklist for Gurgaon bookings through Switch. See exactly what tasks are covered in each booking. Transparent, no-surprises service.`,
    h1: `${s.name} Checklist — What's Included`,
    intro: `Every Switch ${s.name.toLowerCase()} booking in Gurgaon follows a structured checklist so you know exactly what you are getting. No guessing, no shortcuts — just thorough, professional work.`,
    checklistCategories: s.checklistCategories,
    tasks: s.tasks,
    faqs: s.faqs.slice(0, 3),
    prices: s.prices,
    areas: s.areas,
  }
}

function makeFaqPage(s) {
  return {
    slug: `${s.id}-faq-gurgaon`,
    type: 'faq',
    service: s.name,
    serviceId: s.id,
    serviceImg: s.img,
    title: `${s.name} FAQ Gurgaon – Common Questions Answered | Switch`,
    description: `All your questions about hiring a ${s.name.toLowerCase()} in Gurgaon answered. Booking process, pricing, verification, cancellation and more — from Switch.`,
    h1: `${s.name} in Gurgaon – Frequently Asked Questions`,
    intro: `Have questions about booking a ${s.name.toLowerCase()} in Gurgaon? We have answered the most common ones below. If you do not find your answer here, email us at hello@switchlocally.com.`,
    faqs: [
      ...s.faqs,
      { q: `How quickly can I get a ${s.name.toLowerCase()} in Gurgaon?`, a: 'Jyoti alerts the nearest verified workers as soon as you confirm — app ring plus WhatsApp — and you watch the responses live. Pay a little more per hour for a faster yes.' },
      { q: 'Can I cancel my booking?', a: 'Yes. Cancel or reschedule free of charge up to 2 hours before the booking start time through the Switch app.' },
      { q: 'How do I pay?', a: 'Posting is free. When a worker accepts, you pay Switch a ₹99 booking fee. The worker’s fare is paid by you directly to the worker after the work — cash or UPI/QR. Switch takes no cut of the fare.' },
      { q: 'Is Switch available in my area of Gurgaon?', a: `Switch currently operates across ${s.areas.slice(0, 4).join(', ')} and more. Check the app for real-time availability in your sector.` },
    ],
    prices: s.prices,
    areas: s.areas,
    tasks: s.tasks.slice(0, 4),
  }
}

function makeNearMePage(s) {
  return {
    slug: `${s.id}-near-me-gurgaon`,
    type: 'near-me',
    service: s.name,
    serviceId: s.id,
    serviceImg: s.img,
    title: `${s.name} Near Me in Gurgaon | Switch`,
    description: clip(`Find ${s.plural.toLowerCase()} near you in Gurgaon. Jyoti alerts the nearest verified workers first — app ring + WhatsApp. ₹0 to post, ₹99 only after a yes.`),
    h1: `${s.name} Near Me in Gurgaon`,
    intro: `Looking for a ${s.name.toLowerCase()} near you in Gurgaon? Switch uses location matching to find the nearest available verified professional — so you get faster arrivals and lower travel time.`,
    areas: s.areas,
    faqs: s.faqs.slice(0, 4),
    prices: s.prices,
    tasks: s.tasks.slice(0, 6),
    benefits: s.benefits.slice(0, 4),
  }
}

function makeSameDayPage(s) {
  return {
    slug: `same-day-${s.id}-gurgaon`,
    type: 'same-day',
    service: s.name,
    serviceId: s.id,
    serviceImg: s.img,
    title: `Same-Day ${s.name} in Gurgaon | Switch`,
    description: clip(`Need ${s.plural.toLowerCase()} today in Gurgaon? Tell Jyoti the time; she alerts nearby verified workers live. ₹0 to post, ₹99 only when someone says yes.`),
    h1: `Same-Day ${s.name} in Gurgaon`,
    intro: `Urgency happens. Tell Jyoti the time and she alerts verified ${s.plural.toLowerCase()} near you right away — app ring plus WhatsApp. Posting is free; pay a little more per hour and someone usually says yes sooner.`,
    steps: [
      { n: '1', title: 'Tell Jyoti it’s for today', desc: `Say “aaj ${s.name.toLowerCase()} chahiye, 3 baje se” — she asks hours, how many people and your address.` },
      { n: '2', title: 'Confirm for ₹0 and watch it live', desc: 'Nearby verified workers are alerted first. You see who saw it and who said yes as it happens.' },
      { n: '3', title: 'Pay ₹99 after a yes — they’re on the way', desc: `You get the start OTP and live tracking; the worker gets your address. Pay their fare directly after the work.` },
    ],
    faqs: [
      { q: `How fast can I get a ${s.name.toLowerCase()} today?`, a: 'Jyoti alerts nearby workers the moment you confirm, and you watch the responses live. A slightly higher hourly rate usually gets a yes sooner.' },
      { q: 'Is the pricing higher for same-day bookings?', a: 'There is no urgent surcharge from Switch. You set the hourly rate yourself, and you pay the ₹99 booking fee only after a worker accepts.' },
      ...s.faqs.slice(0, 3),
    ],
    prices: s.prices,
    benefits: s.benefits.slice(0, 5),
    areas: s.areas,
  }
}

function makeReviewsPage(s) {
  return {
    slug: `${s.id}-reviews-gurgaon`,
    type: 'reviews',
    service: s.name,
    serviceId: s.id,
    serviceImg: s.img,
    title: `${s.name} Reviews in Gurgaon – Customer Stories | Switch`,
    description: clip(`What Gurgaon businesses say about booking staff through Switch — real customer reviews, plus how booking with Jyoti works.`),
    h1: `${s.name} Reviews in Gurgaon`,
    intro: `Don't just take our word for it. Here is what Gurgaon residents say about booking a ${s.name.toLowerCase()} through Switch. Every review is from a real, completed booking.`,
    reviews: s.reviews,
    faqs: s.faqs.slice(0, 3),
    prices: s.prices,
    benefits: s.benefits.slice(0, 4),
    areas: s.areas.slice(0, 6),
    tasks: s.tasks.slice(0, 5),
  }
}

function makeVerifiedPage(s) {
  return {
    slug: `verified-${s.id}-gurgaon`,
    type: 'verified',
    service: s.name,
    serviceId: s.id,
    serviceImg: s.img,
    title: `Verified ${s.name} in Gurgaon – Background Checked | Switch`,
    description: `All Switch ${s.plural.toLowerCase()} in Gurgaon are verified, background-checked and skills-assessed. Book with confidence knowing every worker is thoroughly vetted.`,
    h1: `Verified ${s.plural} in Gurgaon`,
    intro: `Safety and trust are non-negotiable when you let a ${s.name.toLowerCase()} into your home or workplace. Every Switch ${s.name.toLowerCase()} in Gurgaon goes through a 3-step verification process before taking bookings.`,
    verificationSteps: [
      { title: 'Aadhaar Identity Verification', desc: 'Every worker\'s government-issued Aadhaar is verified through the official UIDAI system to confirm identity.' },
      { title: 'Background & Police Check', desc: 'We run background checks through authorised agencies to flag any criminal history before onboarding.' },
      { title: 'Skills Assessment', desc: `Each ${s.name.toLowerCase()} completes a hands-on skills test in their category before they can accept bookings on Switch.` },
    ],
    faqs: s.faqs,
    tasks: s.tasks,
    prices: s.prices,
    benefits: s.benefits,
    areas: s.areas,
  }
}

// ─── COMPETITOR-KEYWORD ALIAS PAGES ───────────────
// Exact-match landing pages for the head terms consumers actually type
// ("house help", "maid", "bai", "domestic help") — the vocabulary that
// Snabbit ("House Help in 10 Mins") and Pronto rank for and that our
// "Home Cleaning" pages were invisible to. Each maps onto existing service
// content, so there's no separate copy tree to maintain.
const ALIAS_KEYWORDS =
  'house help gurgaon, maid in gurgaon, bai, kaam wali bai, kamwali, domestic help gurgaon, ' +
  'house help near me, maid near me, part time maid gurgaon, full time maid gurgaon, ' +
  'house maid service, housemaid gurgaon, maid service near me, home maid gurgaon'

const ALIASES = [
  // home-help cluster (the Snabbit / Pronto battleground)
  {
    serviceId: 'home-cleaning', term: 'House Help', slug: 'house-help-gurgaon',
    intro: `Looking for reliable house help in Gurgaon? Switch connects you with verified, verified workers for the everyday running of your home — jhadu-pocha, dusting, utensils, laundry and general tidying. Book part-time or full-time in under 2 minutes and pay against a clear invoice — no agency, no hidden charges.`,
    about: [
      `A Switch house help handles the daily running of your Gurgaon home — sweeping and mopping (jhadu-pocha), dusting, washing utensils, laundry, and keeping the kitchen and bathrooms tidy. You choose the exact tasks and hours; the worker fits your routine, not the other way round.`,
      `Unlike a broker-supplied bai, every Switch house help is verified and background-checked, so you know exactly who is entering your home. Book part-time for a couple of hours a day or full-time for the whole day, and pay against a clear invoice.`,
    ],
    faqExtra: [
      { q: 'What is the difference between house help and a maid on Switch?', a: 'They cover the same work — cleaning, mopping, dishwashing, laundry and general chores. "House help" and "maid" are just different words Gurgaon customers use for the same worker.' },
      { q: 'Can I get house help for only 2 hours a day?', a: 'Yes. Choose a part-time slot and the worker will come for the hours you need, daily or on selected days.' },
    ],
  },
  {
    serviceId: 'home-cleaning', term: 'Maid', slug: 'maid-gurgaon',
    intro: `Need a kaam wali bai in Gurgaon? Switch connects you with verified, verified maids for daily jhadu-pocha, bartan, dusting, laundry and cleaning. Set timings that suit you, keep the same maid each day, and pay against a clear invoice — no agency, no hidden charges.`,
    about: [
      `A Switch maid takes care of daily jhadu-pocha, bartan (utensils), dusting, laundry and general cleaning across your flat or kothi. Set the timings that suit you — early morning before work, or afternoon while you're out.`,
      `Every maid on Switch is verified and background-checked, and you can request the same maid each day for consistency. No agency cut — you pay securely in the app againsr the work is finished.`,
    ],
    faqExtra: [
      { q: 'Can I request the same maid every day?', a: 'Yes. Set up a recurring booking in the app and the same verified maid will be assigned wherever possible.' },
      { q: 'Do I need to provide cleaning supplies to the maid?', a: 'The maid brings the cleaning know-how; you provide household supplies and any specific products you prefer.' },
    ],
  },
  {
    serviceId: 'home-cleaning', term: 'Domestic Help', slug: 'domestic-help-gurgaon',
    intro: `Looking for domestic help in Gurgaon? Switch connects you with verified, verified workers for cleaning, mopping, dishwashing, laundry, dusting and light kitchen help — part-time or full-time. Book in under 2 minutes and pay against a clear invoice.`,
    about: [
      `Domestic help on Switch covers the full range of household work in Gurgaon — cleaning, mopping, dishwashing, laundry, dusting and light kitchen help. Hire one worker for everyday chores or build a small routine across the week.`,
      `All domestic helpers are verified and background-checked, available part-time or full-time, and booked by the hour or day. You track them in the app and pay against a clear invoice.`,
    ],
    faqExtra: [
      { q: 'What tasks does domestic help cover?', a: 'Sweeping, mopping, dishwashing, laundry, dusting, bathroom and kitchen cleaning, and general tidying. Tell us your priorities at booking.' },
      { q: 'Is the domestic help verified?', a: 'Yes — every worker is verified and background-checked before taking bookings.' },
    ],
  },
  {
    serviceId: 'home-cleaning', term: 'Maid Near Me', slug: 'maid-near-me-gurgaon',
    intro: `Need a maid near you in Gurgaon? Switch uses location matching to connect you with the closest available verified maid — for faster arrivals and easier same-day slots. Book in under 2 minutes and pay against a clear invoice.`,
    about: [
      `Need a maid near you in Gurgaon right now? Switch matches you with the closest available verified maid using location matching, so arrival times are shorter and same-day slots are easier to fill.`,
      `You get a background-checked worker for daily cleaning, mopping, dishwashing and laundry — booked in under two minutes, tracked in the app, and paid only after the work is done.`,
    ],
    faqExtra: [
      { q: 'How does Switch find a maid near me?', a: 'The app uses your location to match you with the nearest available verified maid in your sector, so you get faster arrivals.' },
      { q: 'Can I get a maid near me today?', a: 'Yes — same-day availability is shown in real time based on maids working close to your area.' },
    ],
  },
  {
    serviceId: 'home-cleaning', term: 'House Help Near Me', slug: 'house-help-near-me-gurgaon',
    intro: `Searching for house help near you in Gurgaon? Switch shows verified workers matched to your location for daily chores — sweeping, mopping, utensils and laundry. Book in under 2 minutes and transparent rates, no hidden charges.`,
    about: [
      `Switch shows you verified house help available near your Gurgaon address, matched by location so the worker can reach you quickly for daily chores — sweeping, mopping, utensils and laundry.`,
      `Every house help near you is verified and background-checked. Book by the hour or day, part-time or full-time, and transparent rates, no hidden charges.`,
    ],
    faqExtra: [
      { q: 'Is there house help available near me right now?', a: 'Open the Switch app and enter your location — real-time availability for house help in your sector is shown instantly.' },
      { q: 'How quickly can house help reach me?', a: 'Because Switch matches the nearest available worker, most same-day bookings are confirmed within a few hours.' },
    ],
  },
  {
    serviceId: 'home-cleaning', term: 'Part Time Maid', slug: 'part-time-maid-gurgaon',
    intro: `Want a part-time maid in Gurgaon? Switch connects you with verified workers for a fixed few hours a day — ideal for daily jhadu-pocha, utensils and a quick tidy without a full-time commitment. Pay by the hour, only after the work is done.`,
    about: [
      `A part-time maid on Switch comes for a fixed few hours each day or on selected days — ideal for daily jhadu-pocha, utensils and a quick tidy without a full-time commitment. You pick the hours; the worker fits your schedule.`,
      `Part-time maids are verified and background-checked, and you can keep the same person for a consistent routine. Pay by the hour, only after the work is done — no agency deposit.`,
    ],
    faqExtra: [
      { q: 'How many hours is a part-time maid booking?', a: 'Typically 1–4 hours a day. Choose the slot that covers your daily chores — sweeping, mopping, dishwashing and dusting.' },
      { q: 'Can a part-time maid come only on alternate days?', a: 'Yes. Set your preferred days in the app and the same maid will come on that schedule.' },
    ],
  },
  {
    serviceId: 'home-cleaning', term: 'Full Time Maid', slug: 'full-time-maid-gurgaon',
    intro: `Need a full-time maid in Gurgaon? Switch connects you with verified workers who cover your household for the whole working day — cleaning, mopping, dishwashing, laundry and kitchen help. Book for a day, a week or an ongoing routine and pay against a clear invoice.`,
    about: [
      `A full-time maid on Switch covers your household for the whole working day — cleaning, mopping, dishwashing, laundry, dusting and kitchen help across all rooms of your Gurgaon home.`,
      `Full-time maids are verified and background-checked. Book for a single day, a week, or an ongoing routine with the same trusted worker, and pay against a clear invoice.`,
    ],
    faqExtra: [
      { q: 'What hours does a full-time maid work?', a: 'A full-time maid typically covers an 8–12 hour day. Choose the plan that matches your household needs.' },
      { q: 'Can I hire a full-time maid on a monthly basis?', a: 'Yes. Set up a recurring booking in the app for the same maid across the month.' },
    ],
  },
  {
    serviceId: 'home-cleaning', term: 'Bathroom Cleaning', slug: 'bathroom-cleaning-gurgaon',
    kw: 'bathroom cleaning gurgaon, toilet cleaning service, washroom cleaning near me, bathroom deep cleaning gurgaon',
    intro: `Book bathroom deep cleaning in Gurgaon with Switch. Verified workers scrub toilets, basins, tiles, taps and floors — removing hard-water stains, soap scum and grime. Pay against a clear invoice.`,
    about: [
      `Switch bathroom cleaning in Gurgaon covers a thorough scrub of toilets, basins, tiles, taps, mirrors and floors — removing the hard-water stains, soap scum and grime that daily cleaning misses.`,
      `Book a verified worker for a one-time deep clean or add bathroom cleaning to a regular schedule. You pay against a clear invoice.`,
    ],
    faqExtra: [
      { q: 'What does bathroom deep cleaning include?', a: 'Scrubbing the toilet, basin, tiles, fittings and floor, descaling taps and glass, and disinfecting all surfaces.' },
      { q: 'How long does bathroom cleaning take?', a: 'A single bathroom deep clean usually takes 45–90 minutes depending on size and condition.' },
    ],
  },
  {
    serviceId: 'home-cleaning', term: 'Kitchen Cleaning', slug: 'kitchen-cleaning-gurgaon',
    kw: 'kitchen cleaning gurgaon, kitchen deep cleaning, chimney cleaning, dishwashing help gurgaon',
    intro: `Book kitchen deep cleaning in Gurgaon with Switch. Verified workers degrease the stovetop and chimney, wipe counters and cabinets, scrub the sink and mop the floor. Pay against a clear invoice.`,
    about: [
      `Kitchen cleaning on Switch tackles the greasy jobs — stovetop and chimney degreasing, counter and cabinet wiping, sink scrubbing, backsplash tiles and floor mopping — for a genuinely clean Gurgaon kitchen.`,
      `Book a verified worker for a one-time kitchen deep clean or as part of a regular routine. You provide the supplies; pay against a clear invoice.`,
    ],
    faqExtra: [
      { q: 'Does kitchen cleaning include the chimney and stovetop?', a: 'Yes — degreasing the stovetop, chimney exterior, tiles and counters is part of a kitchen deep clean.' },
      { q: 'Can I add utensil washing to kitchen cleaning?', a: 'Yes. Mention it at booking and the worker will include dishwashing.' },
    ],
  },
  {
    serviceId: 'home-cleaning', term: 'Deep Cleaning', slug: 'deep-cleaning-gurgaon',
    kw: 'deep cleaning gurgaon, home deep cleaning service, full house deep clean near me',
    intro: `Book a full-home deep clean in Gurgaon with Switch — floors, bathrooms, kitchen, dusting, glass and fans, top to bottom. Ideal before moving in, after renovation or ahead of a festival. Inspect the result, then pay against a clear invoice.`,
    about: [
      `Switch deep cleaning covers the whole home end-to-end — floors, bathrooms, kitchen, dusting, glass, fans and hard-to-reach corners — ideal before moving in, after renovation, or ahead of a festival or party.`,
      `Book one verified worker or a team for larger homes. Everything follows a room-by-room checklist, and you inspect the result before the invoice is raised.`,
    ],
    faqExtra: [
      { q: 'How is deep cleaning different from regular cleaning?', a: 'Deep cleaning is a thorough, top-to-bottom clean including scrubbing, degreasing and detailing — far beyond daily sweeping and mopping.' },
      { q: 'How long does a full-home deep clean take?', a: 'A 2–3 BHK typically takes 6–10 hours; larger homes may need a team or a second day.' },
    ],
  },
  // cook cluster
  {
    serviceId: 'cook', term: 'Bawarchi', slug: 'bawarchi-gurgaon',
    kw: 'bawarchi gurgaon, cook for home gurgaon, house cook, khana banane wali, kitchen cook near me',
    intro: `Need a bawarchi in Gurgaon? Switch connects you with verified home cooks for daily roti, sabzi and dal, rice and pulao, and full spreads for parties — North Indian, Punjabi, South Indian or Mughlai. Pay against a clear invoice.`,
    about: [
      `A bawarchi on Switch is a home cook for your Gurgaon kitchen — daily roti, sabzi and dal, rice and pulao, and full spreads for parties. Choose North Indian, Punjabi, South Indian or Mughlai as you like.`,
      `Every bawarchi is verified and health-screened. You provide the groceries; the cook brings the skill. Book by the meal, day or week and pay against a clear invoice.`,
    ],
    faqExtra: [
      { q: 'Can a bawarchi cook for a party or function?', a: 'Yes. Mention the headcount and menu at booking and we match you with a cook experienced in bulk and party cooking.' },
      { q: 'Do I need to buy the groceries for the bawarchi?', a: 'Yes, you supply the groceries; the bawarchi brings the cooking expertise.' },
    ],
  },
  {
    serviceId: 'cook', term: 'Cook For Home', slug: 'cook-for-home-gurgaon',
    kw: 'cook for home gurgaon, home cook, daily cook, tiffin cook, house cook near me',
    intro: `Looking for a cook for home in Gurgaon? Switch connects you with verified home cooks for fresh, home-style breakfast, lunch, dinner or tiffin — made to your family's taste. Keep the same cook daily and pay against a clear invoice.`,
    about: [
      `A cook for home on Switch prepares fresh, home-style meals in your Gurgaon kitchen — breakfast, lunch, dinner or tiffin — to your family's taste and dietary needs.`,
      `All home cooks are verified and health-screened, and you can request the same cook daily. Book by the meal, day or week and pay against a clear invoice.`,
    ],
    faqExtra: [
      { q: 'Can I hire the same cook for home every day?', a: 'Yes. Set up a recurring booking and request your preferred cook for a consistent daily routine.' },
      { q: 'Can the cook prepare diet-specific meals?', a: 'Yes — low-oil, diabetic-friendly or high-protein meals can be arranged; mention it at booking.' },
    ],
  },
  // childcare cluster
  {
    serviceId: 'nanny', term: 'Babysitter', slug: 'babysitter-gurgaon',
    kw: 'babysitter gurgaon, baby sitter near me, child care, baby care taker, creche help gurgaon',
    intro: `Need a babysitter in Gurgaon? Switch connects you with verified, child-safety-trained workers for feeding, play, naps, homework help and safe supervision — for a few hours or a full day. Pay against a clear invoice.`,
    about: [
      `A babysitter on Switch looks after your child in Gurgaon while you work, run errands or step out for the evening — feeding, play, naps, homework help and safe supervision.`,
      `Every babysitter is verified with an enhanced background check for childcare, and trained in basic child safety. Book for a few hours or a full day and pay against a clear invoice.`,
    ],
    faqExtra: [
      { q: 'What ages can a Switch babysitter care for?', a: 'From newborns through school-age children. Mention your child\'s age at booking so we match the right experience.' },
      { q: 'Can I book a babysitter for just an evening?', a: 'Yes. The 4-hour slot is ideal for an evening out or after-school care.' },
    ],
  },
  {
    serviceId: 'nanny', term: 'Japa Maid', slug: 'japa-maid-gurgaon',
    kw: 'japa maid gurgaon, jappa maid, newborn care, post delivery maid, mother care maid near me',
    intro: `Looking for a japa maid in Gurgaon? Switch connects you with verified workers experienced in post-delivery care — baby bathing and massage, feeding support, and mother's recovery care. Book day or extended care and pay against a clear invoice.`,
    about: [
      `A japa maid on Switch provides specialised post-delivery care for new mothers and newborns in Gurgaon — baby bathing and massage, feeding support, mother's diet and recovery care, and help settling the newborn routine.`,
      `Japa maids are verified and experienced in newborn and post-natal care. Book for day support or extended live-out care and pay against a clear invoice.`,
    ],
    faqExtra: [
      { q: 'What does a japa maid do?', a: 'Newborn bathing and massage, feeding and burping support, mother\'s post-delivery care and diet help, and settling the baby\'s routine.' },
      { q: 'How long can I book a japa maid for?', a: 'From a few hours a day to extended multi-week arrangements during the recovery period.' },
    ],
  },
]

function makeAliasPage(a) {
  const s = SERVICES.find(x => x.id === a.serviceId)
  const bare = a.term.replace(/ near me$/i, '').toLowerCase()
  return {
    slug: a.slug,
    type: 'landing',
    service: a.term,
    serviceId: s.id,
    serviceImg: s.img,
    title: `${a.term} in Gurgaon — Same-Day | Switch`,
    description: clip(`Book a verified ${bare} in Gurgaon by chatting with Jyoti. ₹0 to post, ₹99 only when a worker says yes; the fare goes to the worker. ${a.about[0]}`),
    h1: `${a.term} in Gurgaon`,
    intro: a.intro,
    keywords: a.kw || ALIAS_KEYWORDS,
    uniqueSection: {
      heading: `About ${a.term} in Gurgaon`,
      paragraphs: a.about,
    },
    tasks: s.tasks,
    prices: s.prices,
    faqs: [...a.faqExtra, ...s.faqs],
    reviews: s.reviews,
    benefits: s.benefits,
    areas: s.areas,
    longDesc: s.longDesc,
  }
}

export const ALIAS_PAGES = ALIASES.map(makeAliasPage)

// ─── HYPERLOCAL SERVICE × LOCALITY PAGES ──────────
// Gurgaon-exclusive is our edge: national players (Snabbit, Pronto) rank at
// the city level; we go one level deeper — "maid in DLF Phase 3", "cook in
// Sushant Lok" — capturing high-intent local searches they don't target.
function slugify(t) {
  return t.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/(^-|-$)/g, '')
}

const HYPERLOCAL_TERMS = [
  { term: 'Maid',          serviceId: 'home-cleaning' },
  { term: 'House Help',    serviceId: 'home-cleaning' },
  { term: 'Home Cleaning', serviceId: 'home-cleaning' },
  { term: 'Cook',          serviceId: 'cook' },
  { term: 'Nanny',         serviceId: 'nanny' },
]

// Per-locality facts so every area page carries genuinely unique content
// (pincode, landmarks, neighbouring areas, a character blurb) instead of the
// same boilerplate with one word swapped — this is what makes Google index them.
const LOCALITIES = {
  'DLF Phase 1':      { pincode: '122002', landmarks: ['DLF Galleria Market', 'Rapid Metro Sikanderpur', 'Qutub Enclave'],           nearby: ['Sikanderpur', 'Chakkarpur', 'DLF Phase 2'],              blurb: 'one of Gurgaon\'s oldest planned colonies, full of independent kothis and builder floors' },
  'DLF Phase 2':      { pincode: '122002', landmarks: ['DLF Cyber City', 'Rapid Metro Belvedere Towers', 'DLF Phase 2 Metro'],        nearby: ['Cyber City', 'DLF Phase 3', 'Sikanderpur'],              blurb: 'a residential pocket right beside the Cyber City business hub, mixing condominiums and independent homes' },
  'DLF Phase 3':      { pincode: '122010', landmarks: ['DLF Phase 3 Metro', 'Cyber Hub', 'Chakkarpur Market'],                        nearby: ['Sikanderpur', 'Nathupur', 'DLF Phase 2'],               blurb: 'a dense residential area close to Cyber Hub, popular with working professionals and families' },
  'DLF Phase 4':      { pincode: '122009', landmarks: ['Galleria Market', 'South Point Mall', 'Golf Course Road'],                     nearby: ['DLF Phase 5', 'Sushant Lok', 'Golf Course Road'],        blurb: 'a premium enclave of condominiums near Galleria Market and Golf Course Road' },
  'Sushant Lok':      { pincode: '122009', landmarks: ['Huda City Centre Metro', 'Sector 29 dining hub', 'Sushant Lok Phase 1'],      nearby: ['Sector 29', 'DLF Phase 4', 'Golf Course Road'],          blurb: 'a well-established township of independent houses and builder floors' },
  'Palam Vihar':      { pincode: '122017', landmarks: ['Palam Vihar Market', 'Dwarka Expressway', 'Ansal Plaza'],                     nearby: ['Sector 22', 'Sector 23', 'Dwarka Expressway'],           blurb: 'a large self-contained colony in west Gurgaon with independent homes' },
  'South City':       { pincode: '122001', landmarks: ['South City I', 'Signature Tower', 'Sector 41'],                               nearby: ['Sector 40', 'Sector 30', 'Sohna Road'],                  blurb: 'a set of gated residential blocks off Sohna Road and MG Road' },
  'Sohna Road':       { pincode: '122018', landmarks: ['Vatika Business Park', 'Omaxe Gurgaon Mall', 'Subhash Chowk'],                nearby: ['Sector 48', 'Sector 49', 'South City II'],               blurb: 'a fast-growing corridor of high-rise condominiums along Sohna Road' },
  'Golf Course Road': { pincode: '122002', landmarks: ['DLF Golf & Country Club', 'Sector 42–43', 'Genpact Chowk'],                   nearby: ['DLF Phase 5', 'Sector 53', 'Sushant Lok'],               blurb: 'Gurgaon\'s premium high-rise corridor lined with luxury condominiums' },
  'Nirvana Country':  { pincode: '122018', landmarks: ['Good Earth City Centre', 'Sector 50', 'South City II'],                       nearby: ['Sector 50', 'South City II', 'Sohna Road'],              blurb: 'a gated township of villas and condominiums in South Gurgaon' },
  'Malibu Towne':     { pincode: '122018', landmarks: ['Malibu Towne', 'Sector 47', 'Sohna Road'],                                    nearby: ['Sector 47', 'Sohna Road', 'South City II'],              blurb: 'an established gated community of independent villas' },
  'Sector 14':        { pincode: '122001', landmarks: ['Sector 14 Market', 'Old DLF Colony', 'Gurgaon Bus Stand'],                    nearby: ['Sector 15', 'Sector 4', 'Old DLF Colony'],               blurb: 'one of old Gurgaon\'s prime residential sectors, right by the main market' },
  'Sector 29':        { pincode: '122001', landmarks: ['Leisure Valley Park', 'Sector 29 dining district', 'Huda City Centre Metro'], nearby: ['Sector 28', 'DLF Phase 4', 'Sushant Lok'],               blurb: 'a central sector known for its dining district and proximity to major offices' },
  'Sector 45':        { pincode: '122003', landmarks: ['Huda City Centre Metro', 'Sector 44', 'Sector 46'],                          nearby: ['Sector 44', 'Sector 46', 'South City I'],                blurb: 'a quiet residential sector close to the metro and Golf Course Extension' },
  'Sector 52':        { pincode: '122003', landmarks: ['Ardee City', 'Sun City', 'Golf Course Extension Road'],                       nearby: ['Sector 53', 'Sector 56', 'Golf Course Extension'],       blurb: 'a residential sector with gated colonies like Ardee City and Sun City' },
  'Sector 56':        { pincode: '122011', landmarks: ['Hong Kong Bazaar', 'Uppal Southend', 'Golf Course Extension Road'],           nearby: ['Sector 55', 'Sector 57', 'Golf Course Extension'],       blurb: 'a popular residential sector off Golf Course Extension Road' },
}

const HYPERLOCAL_AREAS = [
  'DLF Phase 1', 'DLF Phase 2', 'DLF Phase 3', 'DLF Phase 4', 'Sushant Lok',
  'Palam Vihar', 'South City', 'Sohna Road', 'Golf Course Road', 'Nirvana Country',
  'Malibu Towne', 'Sector 14', 'Sector 29', 'Sector 45', 'Sector 52', 'Sector 56',
]

function makeAreaPage(t, area) {
  const s = SERVICES.find(x => x.id === t.serviceId)
  const bare = t.term.toLowerCase()
  const al = area.toLowerCase()
  const loc = LOCALITIES[area] || { pincode: '', landmarks: [], nearby: [], blurb: 'a well-connected Gurgaon neighbourhood' }
  const lm = loc.landmarks
  const twoLm = lm.slice(0, 2).join(' and ')
  const pin = loc.pincode ? ` (${loc.pincode})` : ''
  return {
    slug: `${slugify(t.term)}-in-${slugify(area)}-gurgaon`,
    type: 'landing',
    service: t.term,
    serviceId: s.id,
    serviceImg: s.img,
    title: `${t.term} in ${area}, Gurgaon | Switch`,
    description: clip(`Book a verified ${bare} in ${area}, Gurgaon${pin}. Jyoti alerts workers near ${twoLm || area} — ₹0 to post, ₹99 only when someone says yes.`),
    h1: `${t.term} in ${area}, Gurgaon`,
    intro: `Need a reliable ${bare} in ${area}? Switch has verified, verified workers living in and around ${area} — ${loc.blurb}. Whether you're near ${twoLm || area}, a worker can reach you the same day. Book in the app in under 2 minutes — no agency, no hidden charges, pay against a clear invoice.`,
    keywords: `${bare} in ${al}, ${bare} ${al} gurgaon, ${bare} near me ${al}, ${bare} service ${al}, hire ${bare} ${al}${lm[0] ? `, ${bare} near ${lm[0].toLowerCase()}` : ''}`,
    uniqueSection: {
      heading: `${t.term} in ${area} — Local Coverage`,
      paragraphs: [
        `${area}${pin} is ${loc.blurb}. Switch ${s.plural.toLowerCase()} regularly take bookings across ${area}, so most requests near ${twoLm || area} are matched with a worker who already works in the neighbourhood.`,
        `Because our ${bare}s are local to ${area} and adjoining ${loc.nearby.slice(0, 2).join(' and ')}, arrival times are shorter and same-day slots are easier to fill than with a city-wide agency. Book by the hour or day, track the worker in the app, and pay against a clear invoice.`,
      ],
      chipGroups: [
        ...(lm.length ? [{ title: `Spots we cover in ${area}`, chips: lm }] : []),
        ...(loc.nearby.length ? [{ title: 'Nearby areas we also serve', chips: loc.nearby }] : []),
      ],
    },
    tasks: s.tasks,
    prices: s.prices,
    faqs: [
      { q: `Do you provide a ${bare} in ${area}, Gurgaon?`, a: `Yes. Switch has verified ${s.plural.toLowerCase()} serving ${area}${pin} and nearby localities like ${loc.nearby.join(', ')}. Same-day booking is available near ${twoLm || area}.` },
      { q: `How fast can a ${bare} reach ${area}?`, a: `Jyoti alerts workers nearest to ${area} first, so whoever says yes is usually close by. You see their live location once you book.` },
      ...s.faqs,
    ],
    reviews: s.reviews,
    benefits: s.benefits,
    areas: HYPERLOCAL_AREAS.filter(a => a !== area),
    longDesc: `${s.longDesc} In ${area}, Switch is a popular choice for households near ${lm.join(', ') || area} who want a trusted ${bare} without dealing with brokers or agencies.`,
  }
}

export const AREA_PAGES = HYPERLOCAL_TERMS.flatMap(t => HYPERLOCAL_AREAS.map(a => makeAreaPage(t, a)))

// ─── GENERATE ALL PAGES ───────────────────────────

export const SEO_PAGES = [
  ...SERVICES.flatMap(s => [
    makeLandingPage(s),
    makePricingPage(s),
    makeHowToHirePage(s),
    makeBenefitsPage(s),
    makeChecklistPage(s),
    makeFaqPage(s),
    makeNearMePage(s),
    makeSameDayPage(s),
    makeReviewsPage(s),
    makeVerifiedPage(s),
  ]),
  ...ALIAS_PAGES,
  ...AREA_PAGES,
]

// Template variants that repeat their service page almost word for word, and
// area pages that duplicate "Maid in <area>" under another name. They stay
// reachable but are kept out of Google's index (and the sitemap) so the
// stronger page for each search ranks instead of competing with near-copies.
const THIN_TYPES = new Set(['benefits', 'checklist', 'faq', 'reviews', 'verified'])
for (const p of SEO_PAGES) {
  if (THIN_TYPES.has(p.type) || /^(house-help|home-cleaning)-in-/.test(p.slug)) p.noindex = true
}

export function getPageBySlug(slug) {
  return SEO_PAGES.find(p => p.slug === slug) || null
}

export { SERVICE_LIST } from './siteIndex.js'
