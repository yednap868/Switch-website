/* Industry landing pages — /warehouse-staffing-gurgaon, /event-staffing-gurgaon,
   /restaurant-staffing-gurgaon, /office-staffing-gurgaon, /retail-staffing-gurgaon.
   Each page is a hero plus an ordered list of sections; IndustryPage renders
   them in the order given so every page keeps its own narrative. */

export const GURGAON_AREAS = [
  'DLF', 'Sushant Lok', 'Palam Vihar', 'Udyog Vihar', 'Cyber City', 'Sohna Road', 'MG Road', 'Sector 1–49',
]

/* Shared "Why Switch" copy — pages override the entries that are
   written specifically for them. */
const WHY = {
  verified: {
    title: 'Aadhaar-Verified Staff',
    desc: "Every Switch Player goes through the platform's verification process, including document checks and interviews.",
  },
  sameDay: {
    title: 'Staff in a Day',
    desc: 'Browse verified staff, book in a few taps and keep the day moving. The Switch app is built for the moments you need help now.',
  },
  flexible: {
    title: 'Flexible Staffing',
    desc: 'Book workers for a single day, several days or discuss an ongoing requirement.',
  },
  replacement: {
    title: 'Replacement Guarantee',
    desc: 'We back every booking with a replacement guarantee. If a Switch Player is a no-show or not the right fit, we dispatch a replacement fast — usually within 24 hours — so your business stays covered.',
  },
  specific: {
    title: 'Have a Specific Requirement?',
    desc: "Tell Switch what kind of worker you need, how many people you need and when you need them. We'll help you arrange the staffing requirement.",
    cta: true,
  },
  billing: {
    title: 'Simple, Transparent Billing',
    desc: 'One clear rate, no agency commissions or hidden charges. Clean invoices for your business records.',
  },
}

const steps = (place) => [
  {
    title: 'Pick the Staff You Need',
    desc: `Choose the type and number of workers ${place} requires. Set how many workers you need and how long you need them.`,
  },
  {
    title: 'Book in a Few Taps',
    desc: 'Once you’ve selected your workers, simply click “Add to Cart”, review your booking and proceed to checkout.',
  },
  {
    title: 'Your Staff Reports. Booking Confirmed.',
    desc: 'Once your payment is completed at checkout, your booking is confirmed. Your Switch Players arrive for the booking, and OTP verification confirms their arrival.',
  },
]

/* FAQ entries that read the same on every page. */
const FAQ = {
  bulk: {
    q: 'Can I hire multiple Switch Players or a full team?',
    a: 'Yes. Bulk hiring is one of our most common requests — 3, 5 or more Switch Players, including full teams for 7-day blocks. WhatsApp us your requirement for a custom quote and a dedicated point of contact.',
  },
  unlisted: {
    q: 'Can I request a worker type that isn’t listed?',
    a: 'If you have a specific staffing requirement, tell Switch what kind of worker you need, what they will be doing and how many people you need. The team can help with the requirement.',
  },
  verified: {
    q: 'Are Switch workers verified?',
    a: "Switch provides Aadhaar-verified staff who go through the platform's verification process.",
  },
  noShow: {
    q: 'What happens if a worker doesn’t show up?',
    a: 'Switch backs bookings with a replacement guarantee. If a Switch Player is a no-show or isn’t the right fit, a replacement is dispatched fast, usually within 24 hours.',
  },
  trial: {
    q: 'Can I request a trial shift?',
    a: 'Yes. Businesses can request a trial shift before continuing with a longer staffing requirement.',
  },
  help: {
    q: 'What if I need help with my booking?',
    a: 'If you get stuck or need assistance at any point, our support team is available to help you with your booking, worker coordination or any issue that comes up during your staffing requirement.',
  },
}

const cost = (kind) => ({
  q: `How much does ${kind} staffing cost?`,
  a: 'Pricing depends on the worker role, booking duration and number of workers required. You can see the applicable pricing when making a booking. The longer the booking, the lower the rate per Switch Player. For exact rates for your business, talk to us on WhatsApp.',
})

const areas = (h2, lead) => ({ type: 'areas', eyebrow: 'Coverage', h2, lead })

export const INDUSTRY_PAGES = [
  /* ─── WAREHOUSE ─────────────────────────────────── */
  {
    slug: 'warehouse-staffing-gurgaon',
    name: 'Warehouse Staffing',
    title: 'Warehouse Staffing in Gurgaon | Hire Pickers, Packers & Loaders — Switch',
    description:
      'Hire Aadhaar-verified warehouse staff in Gurgaon — pickers, packers, loaders, helpers & delivery executives. Book for a day or longer, replacement guaranteed.',
    keywords:
      'warehouse staffing Gurgaon, warehouse workers Gurgaon, picker packer Gurgaon, loader unloader Gurgaon, warehouse helper Gurgaon, fulfilment staff Gurgaon, dark store staff Gurgaon',
    hero: {
      eyebrow: 'Warehouse Staffing in Gurgaon',
      h1: 'Your Warehouse Runs on People.',
      h1Em: 'Get the Staff to Keep It Moving.',
      lead: 'From picking and packing to loading, unloading, stock movement and dispatch, Switch helps warehouses and fulfilment operations build the workforce they need in Gurgaon.',
      cta: 'Hire Warehouse Staff',
    },
    waMsg: 'Hi Switch — I need warehouse staff in Gurgaon.',
    sections: [
      {
        type: 'intro',
        eyebrow: 'Why staffing matters',
        h2: 'Every Order Has a Workforce Behind It',
        paras: [
          "A warehouse isn't just about storing goods. Every order involves people picking products, packing them, moving stock, loading vehicles and getting shipments ready to leave.",
          "Whether you're setting up a warehouse team, running daily operations or handling a period of high order volume, Switch lets you build the workforce around the work you actually have.",
          'Choose the roles you need, decide how many workers you need and book them for the duration that works for your operation.',
        ],
        callout: {
          title: 'Need workers for your warehouse?',
          text: "Tell us your requirements and we'll help you arrange the right staffing.",
        },
      },
      {
        type: 'roles',
        eyebrow: 'Roles',
        h2: 'Staff for Every Warehouse Need',
        groups: [
          { name: 'Picking & Packing', roles: ['Picker & Packer', 'Warehouse Helper', 'General Helper'] },
          { name: 'Loading & Unloading', roles: ['Loader / Unloader', 'Warehouse Helper', 'General Helper'] },
          { name: 'Warehouse Operations', roles: ['Store Helper', 'Utility', 'Cleaner', 'Housekeeping'] },
          { name: 'Dispatch & Delivery', roles: ['Delivery Executive', 'Picker & Packer', 'General Helper'] },
          { name: 'Security & Support', roles: ['Security Guard', 'Caretaker'] },
        ],
      },
      {
        type: 'cards',
        eyebrow: 'Operations we staff',
        h2: 'Where Switch Fits In',
        items: [
          { title: 'E-commerce & Fulfilment', desc: 'Manage the people-intensive side of online order fulfilment, from incoming inventory through to packed orders leaving the facility.' },
          { title: 'Quick Commerce & Dark Stores', desc: 'Keep fast-moving operations responsive when order volumes, delivery windows and stock movement are constantly changing.' },
          { title: 'Distribution Centres', desc: 'Handle large volumes of incoming and outgoing goods with a workforce that can scale around your operational requirements.' },
          { title: 'Retail Warehouses', desc: 'Support the movement and organisation of inventory between the warehouse and the stores or outlets it serves.' },
          { title: 'Manufacturing & Industrial', desc: 'Keep materials, finished goods and warehouse activity moving alongside your wider production operation.' },
        ],
      },
      {
        type: 'table',
        eyebrow: 'Booking options',
        h2: 'Book Staff Based on Your Warehouse Needs',
        cols: ['Your requirement', 'With Switch'],
        rows: [
          ['A few workers', 'Book individual workers'],
          ['Several different roles', 'Add multiple workers to your cart'],
          ['Staff for one busy day', 'Book staff for the day you need'],
          ['Staff for a longer duration', 'Choose your required duration and get a customised quote'],
          ['Recurring warehouse requirement', 'Discuss your ongoing staffing requirement'],
          ['Warehouses across multiple locations', 'Share your location-wise requirements for coordinated staffing across warehouses'],
        ],
        cta: 'app',
      },
      {
        type: 'flow',
        eyebrow: 'Across the floor',
        h2: 'From Receiving to Dispatch',
        items: [
          { title: 'Receiving & Unloading', desc: 'Get the workforce required when incoming stock needs to be unloaded, moved and organised.' },
          { title: 'Picking & Packing', desc: 'Keep orders moving from shelves to packed shipments with the people needed on the floor.' },
          { title: 'Stock Movement', desc: 'Handle the movement of goods across your warehouse as inventory moves between different stages of the operation.' },
          { title: 'Dispatch', desc: 'Get shipments sorted, moved and prepared for their next destination.' },
        ],
      },
      {
        type: 'why',
        eyebrow: 'Why Switch',
        h2: 'The Switch Difference',
        items: [
          WHY.verified,
          WHY.sameDay,
          { title: 'Multiple Roles Through One Platform', desc: 'From warehouse operations to loading, picking, packing and delivery, manage different staffing requirements through Switch.' },
          WHY.flexible,
          WHY.replacement,
          WHY.specific,
          WHY.billing,
        ],
      },
      { type: 'steps', eyebrow: 'How it works', h2: 'Get Your Team On The Floor In 3 Steps', items: steps('your warehouse') },
      areas('Serving Warehouses Across Gurgaon', 'Switch helps warehouses, fulfilment centres and distribution operations hire staff across Gurgaon, including:'),
      {
        type: 'faq',
        eyebrow: 'FAQs',
        h2: 'Frequently Asked Questions',
        items: [
          { q: 'Can I hire warehouse staff at short notice?', a: 'Yes. Switch helps businesses find workers for urgent and same-day staffing requirements.' },
          { q: 'Can I hire workers for just one day?', a: 'Yes. You can book workers for a single day or make a longer booking depending on your requirement.' },
          FAQ.bulk, FAQ.unlisted, FAQ.verified, FAQ.noShow, FAQ.trial, FAQ.help, cost('warehouse'),
        ],
      },
    ],
  },

  /* ─── EVENTS ────────────────────────────────────── */
  {
    slug: 'event-staffing-gurgaon',
    name: 'Event & Banquet Staffing',
    title: 'Event & Banquet Staffing in Gurgaon | Waiters, Bartenders, Bouncers — Switch',
    description:
      'Hire verified event staff in Gurgaon — waiters, bartenders, cooks, bouncers, promoters & helpers for weddings, parties, corporate events and banquets. Same-day available.',
    keywords:
      'event staffing Gurgaon, banquet staff Gurgaon, wedding waiters Gurgaon, bartender for party Gurgaon, bouncer hire Gurgaon, promoters Gurgaon, catering staff Gurgaon',
    hero: {
      eyebrow: 'Event & Banquet Staffing in Gurgaon',
      h1: 'Have an event coming up?',
      h1Em: 'Get the staff you need to run it.',
      lead: 'From waiters and bartenders to cooks, helpers, bouncers, promoters and other event staff, Switch helps you book workers for weddings, parties, corporate events, exhibitions, banquets and other occasions in Gurgaon.',
      cta: 'Hire Event Staff',
    },
    waMsg: 'Hi Switch — I need staff for an event in Gurgaon.',
    sections: [
      {
        type: 'intro',
        eyebrow: 'Event staffing',
        h2: 'You Have the Event. We Help You Staff It.',
        paras: [
          'Planning an event is one thing. Making sure you have enough people on the ground to run it smoothly is another.',
          "Whether you need extra hands for a wedding, additional service staff for a corporate event, kitchen support for a catering setup or people to handle a sudden shortage, Switch helps you find and book the workers you need.",
          'Tell us what kind of staff you need, how many people you need and when you need them — and get your event staffing sorted without going through a lengthy hiring process.',
        ],
        callout: {
          title: 'Need staff at short notice?',
          text: "Events can change quickly. If you're suddenly short on people, Switch can help you find workers for urgent or same-day requirements.",
        },
      },
      {
        type: 'roles',
        eyebrow: 'Roles',
        h2: 'Event Staff You Can Hire Through Switch',
        groups: [
          { name: 'Guest & Service', roles: ['Waiter', 'Captain', 'Steward', 'Bartender', 'Barista'] },
          { name: 'Kitchen & Food Service', roles: ['Cook', 'Chef', 'Kitchen Helper', 'Utility', 'Dishwashing'] },
          { name: 'Event Support', roles: ['General Helper', 'Cleaner', 'Housekeeping'] },
          { name: 'Security & Crowd Support', roles: ['Bouncer', 'Security Guard'] },
          { name: 'Promotions & Guest Engagement', roles: ['Promoter'] },
          { name: 'Setup & Movement', roles: ['Loader / Unloader', 'Picker & Packer', 'General Helper'] },
        ],
      },
      {
        type: 'cards',
        eyebrow: 'Occasions',
        h2: 'Staff Your Event, Your Way',
        items: [
          { title: 'Weddings & Functions', desc: 'Additional waiters, kitchen staff, helpers, bartenders, bouncers and other support staff for weddings and related functions.' },
          { title: 'Corporate Events', desc: 'Staff for conferences, office events, launches, annual functions and corporate gatherings.' },
          { title: 'Parties & Private Events', desc: 'Get extra service, kitchen, cleaning, security and support staff for private parties and celebrations.' },
          { title: 'Banquets & Large Gatherings', desc: 'Bring in additional workers when you need more people to manage a larger guest count or busy venue.' },
          { title: 'Exhibitions & Brand Activations', desc: 'Promoters, helpers, support staff and other workers for exhibitions, activations and promotional events.' },
          { title: 'Festivals & Seasonal Events', desc: 'Additional workers when footfall increases and your regular team needs extra support.' },
        ],
      },
      {
        type: 'table',
        eyebrow: 'Booking options',
        h2: 'Staffing That Fits Your Event',
        cols: ['Your requirement', 'With Switch'],
        rows: [
          ['A few additional helpers', 'Book individual helpers'],
          ['Several different roles', 'Add multiple workers to your cart'],
          ['Staff for one day', 'Book staff for the day you need'],
          ['Staff for a longer duration', 'Choose your required duration and get a customised quote'],
          ['Last-minute staff shortage', 'Tell us what you need and we’ll help you find the required staff'],
        ],
        cta: 'app',
      },
      {
        type: 'flow',
        eyebrow: 'Start to finish',
        h2: 'From Guest Service to Venue Support',
        items: [
          { title: 'Before the Event', desc: 'Helpers, loaders and support staff can assist with setup, movement and venue preparation.' },
          { title: 'During the Event', desc: 'Waiters, bartenders, captains, stewards, promoters, bouncers and other staff help keep the event running smoothly.' },
          { title: 'After the Event', desc: 'Helpers, cleaning and support staff can help with post-event work and venue cleanup.' },
        ],
      },
      {
        type: 'why',
        eyebrow: 'Why Switch',
        h2: 'Why Choose Switch',
        items: [
          { ...WHY.verified, desc: "Switch Players go through the platform's verification process, including document checks and interviews." },
          WHY.sameDay,
          { title: 'Multiple Roles Through One Platform', desc: 'Need different people for different parts of your event? Book the staff you need for service, kitchen, guest support, setup and more — all through one platform.' },
          WHY.flexible,
          WHY.replacement,
          { ...WHY.specific, desc: "Tell Switch what kind of worker you need, what they will be doing, how many people you need and when you need them. We'll help you arrange the staffing requirement." },
          WHY.billing,
        ],
      },
      { type: 'steps', eyebrow: 'How it works', h2: 'Get Your Team On The Floor In 3 Steps', items: steps('your event') },
      areas('Serving Events Across Gurgaon', 'Switch helps businesses and event organisers hire staff across Gurgaon, including:'),
      {
        type: 'faq',
        eyebrow: 'FAQs',
        h2: 'Frequently Asked Questions',
        items: [
          { q: 'Can I hire event staff at short notice?', a: 'Yes. Switch can help businesses and event organisers find workers for urgent and same-day staffing requirements.' },
          { q: 'Can I hire staff for just one event?', a: 'Yes. You can book workers for a single event or make a longer booking when your event runs across multiple days.' },
          FAQ.bulk, FAQ.unlisted, FAQ.verified, FAQ.noShow,
          { q: FAQ.trial.q, a: 'Yes. Businesses can request a trial shift before continuing with a longer staffing requirement. If a Switch Player isn’t the right fit, we replace them — no questions asked.' },
          cost('event'), FAQ.help,
        ],
      },
    ],
  },

  /* ─── RESTAURANTS ───────────────────────────────── */
  {
    slug: 'restaurant-staffing-gurgaon',
    name: 'Restaurant Staffing',
    title: 'Restaurant Staffing in Gurgaon | Hire Cooks, Waiters & Kitchen Staff — Switch',
    description:
      'Hire verified restaurant staff in Gurgaon — cooks, chefs, waiters, bartenders, baristas & kitchen helpers for restaurants, cafés, QSRs and cloud kitchens. Staff within the day.',
    keywords:
      'restaurant staffing Gurgaon, restaurant staff Gurgaon, hire cook Gurgaon, waiter hire Gurgaon, kitchen helper Gurgaon, cafe staff Gurgaon, cloud kitchen staff Gurgaon, bartender Gurgaon',
    hero: {
      eyebrow: 'Restaurant Staffing in Gurgaon',
      h1: 'Need staff for your restaurant or café?',
      h1Em: 'Hire workers through Switch.',
      lead: "Whether you're looking for kitchen staff, service staff or additional hands for a busy period, Switch helps you find and book workers for your restaurant in Gurgaon.",
      cta: 'Hire Restaurant Staff',
    },
    waMsg: 'Hi Switch — I need staff for my restaurant in Gurgaon.',
    sections: [
      {
        type: 'intro',
        eyebrow: 'Restaurant staffing',
        h2: 'When Your Restaurant Needs More Hands, Switch Has You Covered',
        paras: [
          'Running a restaurant means staffing requirements can change quickly.',
          "You may need extra workers for a busy day, cover for someone who's on leave, staff for a new outlet, or additional hands for an event or festive rush.",
          "And when the requirement is last-minute, you don't have time to wait.",
        ],
        callout: {
          title: 'Need staff today?',
          text: "Don't worry. Switch helps businesses get matched with available workers within the day.",
        },
      },
      {
        type: 'roles',
        eyebrow: 'Roles',
        h2: 'Restaurant Staff You Can Hire Through Switch',
        lead: 'Restaurants often need different people across the kitchen, service, guest experience and day-to-day operations. With Switch, you can book the staff you need based on your requirements.',
        groups: [
          { name: 'Kitchen Staff', roles: ['Cook', 'Chef', 'Kitchen Helper', 'Utility'] },
          { name: 'Service & Beverage Staff', roles: ['Waiter', 'Captain', 'Steward', 'Bartender', 'Barista'] },
          { name: 'Front-of-House Staff', roles: ['Receptionist', 'Promoter', 'General Helper'] },
          { name: 'Support & Facility Staff', roles: ['Cleaner', 'Housekeeping', 'Security Guard', 'Caretaker'] },
          { name: 'Events & Crowd Support', roles: ['Bouncer', 'Promoter', 'General Helper', 'Waiter', 'Bartender'] },
        ],
      },
      {
        type: 'cards',
        eyebrow: 'Situations',
        h2: 'Staffing for Every Restaurant Situation',
        items: [
          { title: 'Busy Days & Peak Footfall', desc: 'Expecting a rush? Add extra workers when your regular team needs support.' },
          { title: 'Staff on Leave', desc: "Someone from your regular team is away? Get additional coverage so operations don't have to slow down." },
          { title: 'Last-Minute Staff Shortage', desc: "A worker didn't turn up? Get help when you suddenly find yourself short-staffed." },
          { title: 'New Restaurant or Outlet', desc: 'Opening a new location? Get the different workers you need to get operations running.' },
          { title: 'Festive & Seasonal Demand', desc: "Diwali, holidays, celebrations and seasonal rushes can bring a sudden increase in customers. Add staff when your normal team isn't enough." },
          { title: 'One-Day Events & Special Requirements', desc: 'Need additional waiters, bartenders, helpers or other staff for a special event or one-day requirement? Switch can help you find available staff for the occasion.' },
          { title: 'Temporary or Short-Term Requirements', desc: "Don't need a permanent hire? Book workers according to the duration your business actually requires." },
        ],
      },
      {
        type: 'list',
        eyebrow: 'Who we staff',
        h2: 'Staffing for Restaurants, Cafés & Food Businesses',
        lead: 'Switch can support staffing requirements for:',
        items: ['Restaurants', 'Cafés', 'QSRs', 'Cloud kitchens', 'Food courts', 'Bars', 'Bakeries', 'Catering businesses'],
      },
      {
        type: 'why',
        eyebrow: 'Why Switch',
        h2: 'Why Restaurants Use Switch',
        items: [
          WHY.verified,
          WHY.sameDay,
          { title: 'Multiple Roles Through One Platform', desc: 'Need a cook, kitchen helper and waiter together? Manage different staffing requirements through one platform.' },
          WHY.flexible,
          WHY.replacement,
          WHY.specific,
          WHY.billing,
        ],
      },
      { type: 'steps', eyebrow: 'How it works', h2: 'Get Your Team On The Floor In 3 Steps', items: steps('your restaurant') },
      {
        type: 'table',
        eyebrow: 'Booking options',
        h2: 'From One Restaurant Worker to a Full Team',
        cols: ['Your requirement', 'With Switch'],
        rows: [
          ['A few workers', 'Book individual workers'],
          ['Several different roles', 'Add multiple workers to your cart'],
          ['Staff for one busy day', 'Book staff for the day you need'],
          ['Staff for a longer duration', 'Choose your required duration and get a customised quote'],
          ['Recurring restaurant requirement', 'Discuss your ongoing staffing requirement'],
          ['Restaurants across multiple locations', 'Share your location-wise requirements for coordinated staffing across restaurants'],
        ],
        cta: 'app',
      },
      areas('Serving Restaurants Across Gurgaon', 'Switch helps restaurants, cafés and food businesses hire staff across Gurgaon, including:'),
      {
        type: 'faq',
        eyebrow: 'FAQs',
        h2: 'Frequently Asked Questions',
        items: [
          { q: 'Can I hire restaurant staff at short notice?', a: 'Yes. Switch helps businesses find workers for urgent and same-day staffing requirements.' },
          { q: 'Can I hire workers for just one day?', a: 'Yes. You can book workers for a single day or make a longer booking depending on your requirement.' },
          FAQ.bulk,
          { q: FAQ.unlisted.q, a: 'If you have a specific requirement, tell Switch what kind of worker you need, what they will be doing and how many people you need.' },
          FAQ.verified, FAQ.noShow, FAQ.trial, FAQ.help, cost('restaurant'),
        ],
      },
    ],
  },

  /* ─── OFFICES ───────────────────────────────────── */
  {
    slug: 'office-staffing-gurgaon',
    name: 'Office & Co-working Staffing',
    title: 'Office & Co-working Staffing in Gurgaon | Office Boys, Housekeeping — Switch',
    description:
      'Hire verified office staff in Gurgaon — office boys, pantry boys, receptionists, housekeeping & security for corporate offices and co-working spaces. Daily or ongoing.',
    keywords:
      'office staffing Gurgaon, office boy Gurgaon, pantry boy Gurgaon, office housekeeping Gurgaon, receptionist hire Gurgaon, coworking staff Gurgaon, facility staff Gurgaon',
    hero: {
      eyebrow: 'Office & Co-working Staffing in Gurgaon',
      h1: 'Need staff for your office or workspace?',
      h1Em: 'Get the support you need through Switch.',
      lead: 'From everyday workplace support to additional hands for a growing team, Switch helps offices and co-working spaces find and book workers in Gurgaon.',
      cta: 'Hire Office Staff',
    },
    waMsg: 'Hi Switch — I need staff for my office in Gurgaon.',
    sections: [
      {
        type: 'intro',
        eyebrow: 'Office staffing',
        h2: 'Staffing Made Simple',
        paras: [
          'From welcoming visitors and keeping common areas in shape to managing pantry requirements and supporting day-to-day operations, workplaces need people behind the scenes to keep everything moving.',
          'Sometimes you need one additional person. Sometimes you need a complete support team. Sometimes the requirement is for a day; sometimes you need people for a longer period.',
          'With Switch, you can book the workers you need based on role, number of people and duration — all through one platform.',
        ],
        callout: {
          title: 'Need additional support for your workplace?',
          text: 'Tell us what you need, how many people you need and when you need them.',
        },
      },
      {
        type: 'roles',
        eyebrow: 'Roles',
        h2: 'Workplace Staff, All In One Place',
        groups: [
          { name: 'Workplace & Housekeeping', roles: ['Housekeeping', 'Cleaner', 'General Helper', 'Utility'] },
          { name: 'Office & Front Desk', roles: ['Office Boy', 'Receptionist', 'Pantry Boy', 'Caretaker'] },
          { name: 'Security & Support', roles: ['Security Guard', 'Store Helper', 'General Helper'] },
          { name: 'Food & Pantry', roles: ['Cook', 'Kitchen Helper', 'Utility'] },
        ],
      },
      {
        type: 'cards',
        eyebrow: 'Workplaces',
        h2: 'Staffing for Every Type of Workplace',
        items: [
          { title: 'Corporate Offices', desc: "Whether you're managing a compact office or a large corporate workspace, Switch can help you arrange additional workforce support as your operational needs change." },
          { title: 'Co-working Spaces', desc: 'Shared workspaces have constantly changing occupancy, members, visitors and daily requirements. Get flexible staffing support as your workspace grows or gets busier.' },
          { title: 'Startups & Growing Companies', desc: 'As teams grow, workplace requirements grow with them. Get additional support without committing to a permanent workforce for every new requirement.' },
          { title: 'Business Centres', desc: 'Keep workplace operations organised when you have multiple companies, visitors and day-to-day activities happening under one roof.' },
          { title: 'Offices with Multiple Locations', desc: 'Coordinate staffing requirements across different workplaces and locations instead of managing every requirement separately.' },
        ],
      },
      {
        type: 'table',
        eyebrow: 'Booking options',
        h2: 'Book Staff Based on Your Office Needs',
        cols: ['Your requirement', 'With Switch'],
        rows: [
          ['A few additional helpers', 'Book individual helpers'],
          ['Several different roles', 'Add multiple workers to your cart'],
          ['Staff for one day', 'Book staff for the day you need'],
          ['Staff for a longer duration', 'Choose your required duration and get a customised quote'],
          ['Ongoing office support', 'Discuss your recurring staffing requirement'],
          ['Multiple office locations', 'Share your location-wise staffing requirement'],
        ],
        cta: 'app',
      },
      {
        type: 'flow',
        eyebrow: 'Across the workplace',
        h2: 'The People Behind a Well-Run Workplace',
        items: [
          { title: 'At the Front', desc: 'Create a welcoming experience for employees, visitors, clients and guests.' },
          { title: 'Behind the Scenes', desc: 'Keep the workplace organised, clean and ready for the people using it every day.' },
          { title: 'Around the Pantry', desc: 'Support everyday food, beverage and pantry requirements without adding unnecessary pressure to your existing team.' },
          { title: 'Across the Workplace', desc: 'From facility support to security and general assistance, get the additional workforce your workplace needs.' },
        ],
      },
      {
        type: 'why',
        eyebrow: 'Why Switch',
        h2: 'Built for the Way Your Workplace Works',
        items: [
          { ...WHY.verified, desc: "Switch Players go through the platform's verification process, including document checks and interviews." },
          WHY.sameDay,
          { title: 'Multiple Roles Through One Platform', desc: 'Handle different staffing requirements in one place, instead of coordinating with multiple sources.' },
          WHY.flexible,
          WHY.replacement,
          WHY.specific,
          WHY.billing,
        ],
      },
      { type: 'steps', eyebrow: 'How it works', h2: 'How to Hire Office Staff with Switch', items: steps('your office') },
      areas('Serving Offices Across Gurgaon', 'Switch helps offices and co-working spaces hire staff across Gurgaon, including:'),
      {
        type: 'faq',
        eyebrow: 'FAQs',
        h2: 'Frequently Asked Questions',
        items: [
          { q: 'Can I hire office staff at short notice?', a: 'Yes. Switch helps businesses find workers for urgent and same-day staffing requirements.' },
          { q: 'Can I hire staff for just one day?', a: 'Yes. You can book workers for a single day or make a longer booking depending on your requirement.' },
          FAQ.bulk,
          { q: 'Can I hire staff for multiple office locations?', a: 'Yes. Share your location-wise requirement with Switch for multiple offices or workplaces.' },
          FAQ.unlisted, FAQ.verified, FAQ.noShow, FAQ.trial, cost('office'), FAQ.help,
        ],
      },
    ],
  },

  /* ─── RETAIL ────────────────────────────────────── */
  {
    slug: 'retail-staffing-gurgaon',
    name: 'Retail & Store Staffing',
    title: 'Retail & Store Staffing in Gurgaon | Store Helpers, Cashiers, Promoters — Switch',
    description:
      'Hire verified retail staff in Gurgaon — store helpers, cashiers, promoters, security guards & stock handlers for stores, supermarkets and outlets. Book for a shift or longer.',
    keywords:
      'retail staffing Gurgaon, store staff Gurgaon, store helper Gurgaon, cashier hire Gurgaon, promoter hire Gurgaon, supermarket staff Gurgaon, retail helper Gurgaon',
    hero: {
      eyebrow: 'Retail & Store Staffing in Gurgaon',
      h1: 'Need staff for your retail store?',
      h1Em: 'Hire workers through Switch.',
      lead: 'From store helpers and cashiers to promoters, security and other support staff, Switch helps retail businesses find and book workers in Gurgaon based on their staffing requirements.',
      cta: 'Hire Retail Staff',
    },
    waMsg: 'Hi Switch — I need staff for my retail store in Gurgaon.',
    sections: [
      {
        type: 'intro',
        eyebrow: 'Retail staffing',
        h2: 'When Your Store Gets Busy, You Need People — Fast',
        paras: [
          'Retail staffing needs can change from one day to the next. A weekend sale, festive rush, sudden staff absence, new stock arriving or a new outlet opening can leave your regular team stretched.',
          "You shouldn't have to go through a lengthy hiring process every time you need a few extra hands.",
          'With Switch, you can book the workers you need based on the role, number of workers and duration of your requirement.',
        ],
        callout: {
          title: 'Need staff today?',
          text: 'Tell us what you need and Switch helps you find available workers within the day, subject to availability.',
        },
      },
      {
        type: 'roles',
        eyebrow: 'Roles',
        h2: 'Retail Staff You Can Hire Through Switch',
        lead: 'Different parts of a retail store need different kinds of support.',
        groups: [
          { name: 'Store Operations', roles: ['Store Helper', 'General Helper', 'Utility'], desc: 'For everyday store support, organising, assisting staff and other operational tasks.' },
          { name: 'Billing & Customer Support', roles: ['Cashier', 'Promoter', 'Receptionist'], desc: 'For billing support, customer-facing activities, promotions and in-store requirements.' },
          { name: 'Security & Store Support', roles: ['Security Guard', 'Cleaner', 'Housekeeping'], desc: 'For security, cleanliness and general support around the store.' },
          { name: 'Stock & Logistics', roles: ['Picker & Packer', 'Loader / Unloader', 'Warehouse Helper', 'Delivery Executive'], desc: 'For stock movement, packing, loading, unloading and delivery-related requirements where applicable.' },
        ],
      },
      {
        type: 'cards',
        eyebrow: 'Situations',
        h2: 'Staffing for the Real Challenges',
        items: [
          { title: 'Festive & Seasonal Rush', desc: "Diwali, holiday shopping and promotional periods can bring a sudden increase in customers. Add workers when your regular team isn't enough." },
          { title: 'Weekend & Peak Footfall', desc: 'Expecting heavier footfall on weekends or during a sale? Get additional support for busy store hours.' },
          { title: 'Staff Shortage', desc: 'A team member is unavailable or you suddenly need extra hands? Book available workers to keep your store running.' },
          { title: 'New Store Opening', desc: 'Opening a new outlet? Get the additional staff you need to help get operations started.' },
          { title: 'Stock Arrival & Inventory Days', desc: 'Large stock deliveries, unloading, sorting or inventory work can require more hands than your regular team.' },
          { title: 'Store Promotions & Brand Activations', desc: 'Running a promotion or in-store activation? Get staff such as promoters or helpers for the requirement.' },
          { title: 'Short-Term Requirements', desc: "Don't need another permanent employee? Book workers according to the duration your business actually requires." },
          { title: 'Multiple Stores', desc: 'Need workers across more than one outlet? Share your requirements and arrange staffing based on your individual store needs.' },
        ],
      },
      {
        type: 'list',
        eyebrow: 'Who we staff',
        h2: 'Staffing for Different Types of Retail Businesses',
        lead: 'Switch can support staffing requirements for:',
        items: ['Retail stores', 'Supermarkets', 'Department stores', 'Fashion & apparel stores', 'Electronics & mobile stores', 'Grocery & convenience stores', 'Beauty & lifestyle stores', 'Specialty stores', 'Shopping outlets'],
      },
      {
        type: 'table',
        eyebrow: 'Booking options',
        h2: 'Whatever Your Store Needs, Book the Right Support',
        lead: "Retail staffing doesn't always mean hiring an entire team.",
        cols: ['Your requirement', 'What you can do'],
        rows: [
          ['One store helper', 'Book an individual Switch Player'],
          ['Extra support for a busy day', 'Book additional workers'],
          ['A cashier for a shift', 'Book a cashier for the required duration'],
          ['Promoters for an activation', 'Book promoters for your requirement'],
          ['Help with stock movement', 'Book loaders, helpers or other available workers'],
          ['Staff for a longer duration', 'Choose your required duration and get a customised quote'],
          ['Multiple outlets', 'Share your store-wise staffing requirement'],
        ],
      },
      {
        type: 'why',
        eyebrow: 'Why Switch',
        h2: 'Why Retail Businesses Use Switch',
        items: [
          { ...WHY.verified, desc: "Switch Players go through the platform's verification process, including document checks and interviews." },
          { title: 'Staff in a Day', desc: 'Tell Switch what your store needs and get matched with suitable available workers within the day.' },
          { title: 'Multiple Roles Through One Platform', desc: "Whether you're staffing the shop floor, managing billing counters or preparing for a major sale, book the different workers your store needs through Switch — all in one place." },
          WHY.flexible,
          WHY.replacement,
          { ...WHY.specific, desc: "Don't see exactly the type of worker you're looking for? Tell Switch what kind of worker you need, how many you need and when you need them. We'll help arrange staff based on your requirements." },
          { ...WHY.billing, title: 'Transparent Business Billing' },
        ],
      },
      { type: 'steps', eyebrow: 'How it works', h2: 'How to Hire Retail Staff with Switch', items: steps('your store') },
      {
        type: 'flow',
        eyebrow: 'Any scale',
        h2: 'Built for Retail Staffing — From One Store to Multiple Outlets',
        lead: "Whether you're an independent store or managing several locations, you can arrange staffing according to your operational needs.",
        items: [
          { title: 'One store', desc: 'Need an additional store helper for a busy day.' },
          { title: 'One outlet + peak period', desc: 'Need extra helpers and promoters during a festive sale.' },
          { title: 'Multiple outlets', desc: 'Need several workers across different stores.' },
          { title: 'Ongoing requirement', desc: 'Need a larger team for weekly staffing.' },
        ],
      },
      areas('Serving Retail Businesses Across Gurgaon', 'Switch helps stores, supermarkets and retail outlets hire staff across Gurgaon, including:'),
      {
        type: 'faq',
        eyebrow: 'FAQs',
        h2: 'Frequently Asked Questions',
        items: [
          { q: 'Can I hire retail staff at short notice?', a: 'Yes. Switch helps businesses find available workers for urgent and same-day staffing requirements, subject to availability.' },
          { q: 'Can I hire staff for just one day?', a: 'Yes. You can book workers for a single day or make a longer booking depending on your requirement.' },
          FAQ.bulk,
          { q: 'Can I hire staff for multiple store locations?', a: 'Yes. Share your location-wise requirement with Switch for multiple stores or outlets.' },
          { q: 'Can I hire a worker for a requirement that isn’t listed?', a: 'Yes. Tell Switch what kind of worker you need, what the work involves and when you need them. Switch can help you arrange the staff based on your requirement.' },
          { q: 'Are the workers verified?', a: 'Yes. Switch Players are Aadhaar-verified, document-checked and interviewed before reaching the worksite.' },
          { q: 'What happens if a booked worker doesn’t show up?', a: 'Switch provides a replacement guarantee for every booking. If a Switch Player is a no-show or not the right fit, we dispatch a replacement fast — usually within 24 hours — so your business stays covered.' },
          { q: 'Can I request a trial shift before hiring a worker for longer?', a: 'Yes. Switch allows businesses to request a trial shift to assess the fit before committing to a longer requirement.' },
          cost('retail'), FAQ.help,
        ],
      },
    ],
  },
]

export const getIndustryPage = (slug) => INDUSTRY_PAGES.find((p) => p.slug === slug)
