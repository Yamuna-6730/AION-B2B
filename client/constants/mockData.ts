export interface Company {
  id: string;
  name: string;
  logo: string;
  industry: string;
  founded: number;
  headquarters: string;
  employees: number;
  revenue: string;
  techStack: {
    cloud: string[];
    languages: string[];
    frameworks: string[];
    databases: string[];
    ai: string[];
    devops: string[];
  };
  latestNews: {
    headline: string;
    date: string;
    source: string;
    citation: string;
    summary: string;
  }[];
  funding: {
    total: string;
    recentRound: string;
    investors: string[];
  };
  hiringTrend: string;
  opportunityScore: number;
  icpMatch: number;
  businessDna: {
    innovation: number;
    growth: number;
    hiring: number;
    technology: number;
    security: number;
    cloud: number;
    aiAdoption: number;
    investment: number;
    compliance: number;
  };
  confidence: number;
  recommendation: string;
  recentSignals: {
    type: 'funding' | 'hiring' | 'leadership' | 'expansion' | 'technology' | 'acquisition' | 'partnership' | 'office';
    title: string;
    description: string;
    date: string;
    confidence: number;
  }[];
  decisionMakers: {
    name: string;
    role: string;
    influence: 'High' | 'Medium' | 'Low';
    email: string;
    phone: string;
    linkedin: string;
    avatar: string;
    confidence: number;
    talkingPoints: string[];
  }[];
  competitors: { name: string; matchScore: number }[];
  partners: { name: string; relation: string }[];
  evidence: {
    label: string;
    confidence: number;
  }[];
  simulation: {
    action: string;
    probability: number;
    projectedRevenue: string;
    timeframe: string;
  }[];
}

export const mockCompanies: Company[] = [
  {
    id: "siemens",
    name: "Siemens AG",
    logo: "S",
    industry: "Industrial Manufacturing",
    founded: 1847,
    headquarters: "Munich, Germany",
    employees: 320000,
    revenue: "€78.8B",
    techStack: {
      cloud: ["AWS", "Azure"],
      languages: ["C++", "Java", "Python", "TypeScript"],
      frameworks: ["React", "Spring Boot", "Next.js"],
      databases: ["PostgreSQL", "SAP HANA", "MongoDB"],
      ai: ["TensorFlow", "OpenAI API", "Siemens Industrial Edge AI"],
      devops: ["Kubernetes", "Docker", "GitLab CI", "Terraform"]
    },
    latestNews: [
      {
        headline: "Siemens expands partnership with Microsoft to accelerate industrial AI adoption",
        date: "2026-05-14",
        source: "Financial Times",
        citation: "FT-2026-981",
        summary: "Siemens is integrating Microsoft Azure OpenAI Service into its industrial automation platforms to help factories deploy generative AI assistants for maintenance and quality assurance."
      },
      {
        headline: "Siemens launches AI-enabled digital twin platform for smart infrastructure",
        date: "2026-03-22",
        source: "TechCrunch",
        citation: "TC-2026-443",
        summary: "The company unveiled its next-generation digital twin infrastructure, allowing industrial clients to simulate power grids and manufacturing plants with real-time anomaly detection."
      }
    ],
    funding: {
      total: "N/A (Publicly Traded)",
      recentRound: "N/A",
      investors: ["Public Shareholders", "Institutional Investors"]
    },
    hiringTrend: "Aggressively hiring Applied AI Researchers and Smart Factory Systems Architects in Germany.",
    opportunityScore: 94,
    icpMatch: 95,
    businessDna: {
      innovation: 89,
      growth: 72,
      hiring: 85,
      technology: 92,
      security: 90,
      cloud: 88,
      aiAdoption: 95,
      investment: 82,
      compliance: 96
    },
    confidence: 96,
    recommendation: "Target Siemens Digital Industries division. Propose our agentic validation service to test and optimize their predictive maintenance pipelines.",
    recentSignals: [
      {
        type: "expansion",
        title: "Industrial AI Division Expansion",
        description: "Opening a new AI Center of Excellence in Munich, adding 200+ neural network engineering roles.",
        date: "2026-06-10",
        confidence: 98
      },
      {
        type: "technology",
        title: "Edge AI Software Deployments",
        description: "Upgraded 40+ factories with Edge-LLM technology to translate machine errors to human instructions.",
        date: "2026-05-30",
        confidence: 95
      },
      {
        type: "hiring",
        title: "Hiring 75+ AI Engineers",
        description: "Open requisitions for Computer Vision and PLC AI integration specialists detected across Nuremberg and Munich.",
        date: "2026-06-18",
        confidence: 92
      }
    ],
    decisionMakers: [
      {
        name: "Dr. Roland Busch",
        role: "Chief Executive Officer",
        influence: "High",
        email: "roland.busch@siemens.com",
        phone: "+49 89 636 00",
        linkedin: "linkedin.com/in/rolandbusch",
        avatar: "/avatars/roland.jpg",
        confidence: 92,
        talkingPoints: [
          "Reference Siemens' goals for automation and double-digit digital business growth.",
          "Discuss reducing factory downtime via automated multi-agent diagnostic workflows.",
          "Align with their open digital platform, Siemens Xcelerator."
        ]
      },
      {
        name: "Dr. Hanna Hennig",
        role: "Chief Information Officer",
        influence: "High",
        email: "hanna.hennig@siemens.com",
        phone: "+49 89 636 44",
        linkedin: "linkedin.com/in/hannahennig",
        avatar: "/avatars/hanna.jpg",
        confidence: 95,
        talkingPoints: [
          "Address how AION bridges legacy industrial databases with modern agent architectures.",
          "Provide guarantees on data privacy and local European hosting compatibility (GDPR).",
          "Highlight cost efficiencies in multi-cloud AI infrastructure deployments."
        ]
      }
    ],
    competitors: [
      { name: "General Electric", matchScore: 82 },
      { name: "Schneider Electric", matchScore: 78 },
      { name: "ABB Ltd", matchScore: 85 }
    ],
    partners: [
      { name: "Microsoft", relation: "Cloud & Industrial AI Co-developer" },
      { name: "NVIDIA", relation: "Digital Twin & Omniverse Integration Partner" }
    ],
    evidence: [
      { label: "German Industry 4.0 Expansion Signals", confidence: 97 },
      { label: "Active job posts for PyTorch & Siemens Edge", confidence: 94 },
      { label: "Recent patent applications on Edge LLMs for PLCs", confidence: 90 },
      { label: "Public collaboration updates on Microsoft Azure OpenAI", confidence: 98 }
    ],
    simulation: [
      {
        action: "Propose Pilot with Digital Industries",
        probability: 72,
        projectedRevenue: "€450,000",
        timeframe: "3 Months"
      },
      {
        action: "Conduct Executive Briefing for CIO",
        probability: 88,
        projectedRevenue: "€0",
        timeframe: "1 Month"
      },
      {
        action: "Wait for Next Quarter Procurement Cycle",
        probability: 10,
        projectedRevenue: "€0",
        timeframe: "6 Months"
      }
    ]
  },
  {
    id: "bmw",
    name: "BMW Group",
    logo: "B",
    industry: "Automotive Manufacturing",
    founded: 1916,
    headquarters: "Munich, Germany",
    employees: 150000,
    revenue: "€155.5B",
    techStack: {
      cloud: ["Azure", "AWS"],
      languages: ["C++", "Python", "Go", "TypeScript"],
      frameworks: ["React", "FastAPI", "ROS (Robot Operating System)"],
      databases: ["PostgreSQL", "InfluxDB", "Redis"],
      ai: ["PyTorch", "NVIDIA Omniverse", "Computer Vision models"],
      devops: ["Kubernetes", "Jenkins", "Ansible", "ArgoCD"]
    },
    latestNews: [
      {
        headline: "BMW integrates humanoid robots in manufacturing plants to run AI diagnostics",
        date: "2026-06-02",
        source: "Reuters",
        citation: "RT-2026-112",
        summary: "BMW completed its first trial of Figure humanoid robots in Spartanburg plant, leveraging generative AI to perform tactile verification of parts."
      }
    ],
    funding: {
      total: "N/A (Public)",
      recentRound: "N/A",
      investors: ["Quandt Family", "Public Shareholders"]
    },
    hiringTrend: "Hiring Robotics Integration Engineers, Autonomous Driving System Developers, and Manufacturing Optimization Specialists.",
    opportunityScore: 89,
    icpMatch: 92,
    businessDna: {
      innovation: 92,
      growth: 68,
      hiring: 80,
      technology: 90,
      security: 88,
      cloud: 85,
      aiAdoption: 91,
      investment: 78,
      compliance: 94
    },
    confidence: 91,
    recommendation: "Position AION as the core coordinator for their supply chain digital twin twins to run risk forecasting simulations.",
    recentSignals: [
      {
        type: "technology",
        title: "Humanoid Robots Deployment",
        description: "Deploying Figure 02 robots powered by neural network control models to inspect sheet metal fit.",
        date: "2026-06-02",
        confidence: 96
      },
      {
        type: "expansion",
        title: "Expanded EV Battery Assembly",
        description: "Investing €650M in Munich factory refitting for next-gen Neue Klasse EV batteries.",
        date: "2026-04-10",
        confidence: 99
      }
    ],
    decisionMakers: [
      {
        name: "Oliver Zipse",
        role: "Chairman of the Board of Management",
        influence: "High",
        email: "oliver.zipse@bmw.de",
        phone: "+49 89 382 0",
        linkedin: "linkedin.com/in/oliverzipse",
        avatar: "/avatars/oliver.jpg",
        confidence: 88,
        talkingPoints: [
          "Connect with BMW's 'Neue Klasse' product roadmap and its tech-first philosophy.",
          "Discuss manufacturing cost reduction via predictive simulations.",
          "Emphasize high flexibility in European manufacturing pipelines."
        ]
      }
    ],
    competitors: [
      { name: "Mercedes-Benz", matchScore: 90 },
      { name: "Tesla Inc.", matchScore: 85 },
      { name: "Audi AG", matchScore: 88 }
    ],
    partners: [
      { name: "Figure AI", relation: "Humanoid Robotics Development Partner" },
      { name: "NVIDIA", relation: "Smart Factory Simulation Partner" }
    ],
    evidence: [
      { label: " Neue Klasse EV battery software integration", confidence: 95 },
      { label: "Trial contract announcements with Figure Robotics", confidence: 98 },
      { label: "Active job openings for ROS & Robot Control Systems", confidence: 88 }
    ],
    simulation: [
      {
        action: "Partner with Neue Klasse Supply Chain Division",
        probability: 65,
        projectedRevenue: "€750,000",
        timeframe: "4 Months"
      },
      {
        action: "Deliver Proof of Concept on Figure 02 Diagnostics",
        probability: 50,
        projectedRevenue: "€300,000",
        timeframe: "3 Months"
      }
    ]
  },
  {
    id: "openai",
    name: "OpenAI",
    logo: "O",
    industry: "Artificial Intelligence",
    founded: 2015,
    headquarters: "San Francisco, CA, USA",
    employees: 2500,
    revenue: "$5.8B",
    techStack: {
      cloud: ["Azure", "Cloudflare"],
      languages: ["Python", "C++", "Rust", "TypeScript"],
      frameworks: ["PyTorch", "Next.js", "FastAPI", "Ray"],
      databases: ["PostgreSQL", "Redis", "Pinecone", "Milvus"],
      ai: ["GPT-4/GPT-5", "Sora", "DALL-E", "Reinforcement Learning"],
      devops: ["Kubernetes", "Docker", "Terraform", "GitHub Actions"]
    },
    latestNews: [
      {
        headline: "OpenAI launches GPT-5 with agentic planning and advanced memory architecture",
        date: "2026-05-18",
        source: "The Verge",
        citation: "TV-2026-102",
        summary: "OpenAI unveiled GPT-5, introducing state-of-the-art agentic routing systems, allowing recursive code writing and long-term memory across sessions."
      }
    ],
    funding: {
      total: "$22.5B",
      recentRound: "$6.6B Series H",
      investors: ["Microsoft", "Thrive Capital", "NVIDIA", "Khosla Ventures"]
    },
    hiringTrend: "Aggressively hiring Research Scientists (ML), Security Engineers, and Platform Infrastructure Engineers.",
    opportunityScore: 98,
    icpMatch: 97,
    businessDna: {
      innovation: 99,
      growth: 98,
      hiring: 95,
      technology: 99,
      security: 82,
      cloud: 96,
      aiAdoption: 100,
      investment: 97,
      compliance: 75
    },
    confidence: 98,
    recommendation: "Propose AION's multi-agent compliance validation workflows to help secure OpenAI's agentic deployments against prompt-injection and state violations.",
    recentSignals: [
      {
        type: "funding",
        title: "$6.6B Series H Funding",
        description: "Valuation surges to $157B to scale compute infrastructure and recruit world-class AI researchers.",
        date: "2026-04-05",
        confidence: 100
      },
      {
        type: "hiring",
        title: "Hiring ML Infrastructure Engineers",
        description: "Detected a 35% surge in open roles targeting large-scale distributed training on Kubernetes.",
        date: "2026-06-25",
        confidence: 96
      },
      {
        type: "technology",
        title: "GPT-5 Deployment",
        description: "Rolled out next-gen models supporting agentic planning nodes.",
        date: "2026-05-18",
        confidence: 98
      }
    ],
    decisionMakers: [
      {
        name: "Sam Altman",
        role: "Chief Executive Officer",
        influence: "High",
        email: "altman@openai.com",
        phone: "+1 (415) 555-0199",
        linkedin: "linkedin.com/in/samaltman",
        avatar: "/avatars/sam.jpg",
        confidence: 95,
        talkingPoints: [
          "Connect pitch with safe, scalable AGI infrastructure.",
          "Discuss solving complex workflows in B2B discovery where raw LLMs fail without memory state layers.",
          "Focus on enterprise security integrations."
        ]
      },
      {
        name: "Mira Murati",
        role: "Chief Technology Officer",
        influence: "High",
        email: "mira@openai.com",
        phone: "+1 (415) 555-0155",
        linkedin: "linkedin.com/in/miramurati",
        avatar: "/avatars/mira.jpg",
        confidence: 97,
        talkingPoints: [
          "Focus on our state-of-the-art physics-based Knowledge Graph layout.",
          "Demonstrate deterministic testing of non-deterministic agent pathways.",
          "Benchmark latency and tokens-per-second reduction of routing pipelines."
        ]
      }
    ],
    competitors: [
      { name: "Anthropic", matchScore: 98 },
      { name: "Google DeepMind", matchScore: 96 },
      { name: "Meta AI", matchScore: 92 }
    ],
    partners: [
      { name: "Microsoft", relation: "Primary Cloud & Distribution Partner" },
      { name: "Apple", relation: "iOS Siri Integration Partner" }
    ],
    evidence: [
      { label: "Active job posts for AI Safety and Compliance", confidence: 95 },
      { label: "Series H SEC filings listing computing goals", confidence: 100 },
      { label: "GPT-5 benchmark data and API integration trials", confidence: 98 },
      { label: "Enterprise license agreements with Fortune 500s", confidence: 92 }
    ],
    simulation: [
      {
        action: "Integrate AION inside ChatGPT Enterprise Store",
        probability: 80,
        projectedRevenue: "$2,200,000",
        timeframe: "3 Months"
      },
      {
        action: "Secure Private Model Fine-Tuning Agreement",
        probability: 58,
        projectedRevenue: "$1,500,000",
        timeframe: "6 Months"
      }
    ]
  },
  {
    id: "crowdstrike",
    name: "CrowdStrike Holdings",
    logo: "C",
    industry: "Cybersecurity Software",
    founded: 2011,
    headquarters: "Austin, TX, USA",
    employees: 8500,
    revenue: "$3.1B",
    techStack: {
      cloud: ["AWS", "GCP"],
      languages: ["Go", "Rust", "Python", "C++"],
      frameworks: ["React", "Next.js", "Gin", "Tokio"],
      databases: ["Cassandra", "Elasticsearch", "PostgreSQL", "Redis"],
      ai: ["CrowdStrike Charlotte AI", "Anomaly Detection Models"],
      devops: ["Kubernetes", "Docker", "Terraform", "Spinnaker"]
    },
    latestNews: [
      {
        headline: "CrowdStrike expands European Cloud Security footprint with new Munich datacenter",
        date: "2026-06-15",
        source: "Wall Street Journal",
        citation: "WSJ-2026-118",
        summary: "CrowdStrike has launched a local cloud security sovereign facility in Frankfurt and Munich to accommodate strict European compliance demands."
      }
    ],
    funding: {
      total: "N/A (Publicly Traded)",
      recentRound: "N/A",
      investors: ["Institutional Investors", "Vanguard", "BlackRock"]
    },
    hiringTrend: "Expanding European Sales & Engineering divisions. Hiring Security Researchers and cloud engineers in Frankfurt, London, and Munich.",
    opportunityScore: 92,
    icpMatch: 94,
    businessDna: {
      innovation: 88,
      growth: 86,
      hiring: 92,
      technology: 94,
      security: 98,
      cloud: 95,
      aiAdoption: 89,
      investment: 80,
      compliance: 92
    },
    confidence: 95,
    recommendation: "Pitch our B2B Discovery and buying window predictions to target cybersecurity buyers in Germany and France.",
    recentSignals: [
      {
        type: "expansion",
        title: "European Sovereign Cloud Hub",
        description: "Launching dedicated localized services in Germany to capture EU financial and government entities.",
        date: "2026-06-15",
        confidence: 98
      },
      {
        type: "hiring",
        title: "European Enterprise Sales Hiring",
        description: "Hiring 20+ Account Executives in Frankfurt and Paris targeting Manufacturing sectors.",
        date: "2026-06-20",
        confidence: 94
      }
    ],
    decisionMakers: [
      {
        name: "George Kurtz",
        role: "Chief Executive Officer",
        influence: "High",
        email: "gkurtz@crowdstrike.com",
        phone: "+1 (512) 555-0100",
        linkedin: "linkedin.com/in/georgekurtz",
        avatar: "/avatars/george.jpg",
        confidence: 90,
        talkingPoints: [
          "Focus on automated endpoint discovery and mapping enterprise attack vectors.",
          "Discuss leveraging AI to find shadow IT in European subsidiaries.",
          "Align with their mission of 'stopping breaches' in real-time."
        ]
      }
    ],
    competitors: [
      { name: "SentinelOne", matchScore: 92 },
      { name: "Microsoft Security", matchScore: 89 },
      { name: "Palo Alto Networks", matchScore: 91 }
    ],
    partners: [
      { name: "AWS", relation: "Primary Hosting & Co-selling Platform" },
      { name: "Dell Technologies", relation: "Hardware Distribution Partner" }
    ],
    evidence: [
      { label: "Active job requisitions in Germany", confidence: 96 },
      { label: "Press releases on European Sovereign Cloud Hub", confidence: 98 },
      { label: "Corporate registry listings of new office entities in Munich", confidence: 92 }
    ],
    simulation: [
      {
        action: "Provide European Account Expansion Data Pack",
        probability: 85,
        projectedRevenue: "$180,000",
        timeframe: "1 Month"
      },
      {
        action: "Integrate AION Signals with Charlotte AI",
        probability: 45,
        projectedRevenue: "$1,200,000",
        timeframe: "6 Months"
      }
    ]
  }
];

export interface Mission {
  id: string;
  name: string;
  status: 'Running' | 'Thinking' | 'Completed' | 'Failed';
  query: string;
  timestamp: string;
  plannerState: string;
  agentsActive: number;
  companiesFound: number;
  elapsedTime: string;
  confidence: number;
  activityLog: {
    time: string;
    message: string;
    type: 'info' | 'success' | 'warning' | 'error';
  }[];
  consoleStream: string[];
}

export const mockMissions: Mission[] = [
  {
    id: "mission-1",
    name: "Manufacturing AI Exploration",
    status: "Completed",
    query: "Find Manufacturing companies in Germany expanding into AI.",
    timestamp: "2026-06-27T17:15:00Z",
    plannerState: "Ready",
    agentsActive: 0,
    companiesFound: 48,
    elapsedTime: "00:23",
    confidence: 92,
    activityLog: [
      { time: "17:15:01", message: "Planner Started", type: "info" },
      { time: "17:15:05", message: "Market Agent launched (Scanned 14k domains)", type: "info" },
      { time: "17:15:09", message: "Hiring Agent detected AI engineer job openings", type: "info" },
      { time: "17:15:12", message: "Funding Agent validated corporate capital reserves", type: "info" },
      { time: "17:15:15", message: "Knowledge Graph constructed with 12 initial clusters", type: "success" },
      { time: "17:15:20", message: "Validation Agent confirmed revenue > €10M", type: "success" },
      { time: "17:15:23", message: "Intelligence Scoring complete. 48 companies verified.", type: "success" }
    ],
    consoleStream: [
      "Planner: Thinking...",
      "Market Agent: Scanning corporate portfolios...",
      "Hiring Agent: Fetching active job databases...",
      "Knowledge Graph: Synced with 12 company structures...",
      "Validation Agent: Checked revenue boundaries...",
      "Confidence Level: 92%",
      "Memory State: Saved."
    ]
  },
  {
    id: "mission-2",
    name: "Cybersecurity European Expansion",
    status: "Running",
    query: "Find cybersecurity companies expanding into Europe.",
    timestamp: "2026-06-27T17:30:00Z",
    plannerState: "Thinking",
    agentsActive: 7,
    companiesFound: 12,
    elapsedTime: "00:15",
    confidence: 95,
    activityLog: [
      { time: "17:30:01", message: "Planner initialized query strategy", type: "info" },
      { time: "17:30:04", message: "Discovering Signals (Funding, Hiring, Office lease filings)", type: "info" },
      { time: "17:30:08", message: "Hiring Agent located new offices in Frankfurt & Munich", type: "info" },
      { time: "17:30:12", message: "Connecting Evidence and building Hypotheses", type: "info" }
    ],
    consoleStream: [
      "Planner: Query routing active...",
      "Discovering Signals: Scanning European subsidiaries...",
      "Connecting Evidence: Pulling SEC and EU registry files...",
      "Hiring Agent: Querying Munich job boards...",
      "Current Matches: 12 candidates found...",
      "Confidence: 95%"
    ]
  }
];

export const suggestedMissions = [
  {
    title: "Monitor Market",
    description: "Scan active B2B signals and identify new market entrants daily.",
    icon: "Activity"
  },
  {
    title: "Generate Prospect List",
    description: "Search SaaS or industrial players matching strict ICP parameters.",
    icon: "Users"
  },
  {
    title: "Analyze Competitors",
    description: "Map technology stack overlays and structural overlaps of direct rivals.",
    icon: "Target"
  },
  {
    title: "Predict Buying Windows",
    description: "Detect budget expansions, funding events, or leadership hires.",
    icon: "Clock"
  },
  {
    title: "Find Decision Makers",
    description: "Extract high-influence profiles and personalize sales talking points.",
    icon: "ShieldAlert"
  },
  {
    title: "Executive Briefing",
    description: "Compile data into a downloadable board-ready discovery report.",
    icon: "FileText"
  }
];
