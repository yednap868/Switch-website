import { ProfileHeader } from "@/components/profile/ProfileHeader";
import { AudioPlayer } from "@/components/profile/AudioPlayer";
import { SectionLabel } from "@/components/profile/SectionLabel";
import { StrengthsList } from "@/components/profile/StrengthsList";
import { ProofOfWork } from "@/components/profile/ProofOfWork";
import { ThoughtCard } from "@/components/profile/ThoughtCard";
import { IdealOpportunities } from "@/components/profile/IdealOpportunities";
import { VanceBadge } from "@/components/profile/VanceBadge";
import { ActivityCard } from "@/components/profile/ActivityCard";
import { ProfileBasics } from "@/components/profile/ProfileBasics";
import { ProfileSkills } from "@/components/profile/ProfileSkills";
import { ProfileLinks } from "@/components/profile/ProfileLinks";
import { ProfileNarratives } from "@/components/profile/ProfileNarratives";
import { useQuery } from "@tanstack/react-query";
import { useParams } from "react-router-dom";

type Strength = {
  text: string;
  hasAudio: boolean;
};

type ProofItem = {
  company: string;
  description: string;
  impact: string;
  link: string;
};

type Thought = {
  content: string;
  topic: string;
};

type Opportunities = {
  role: string;
  industries: string[];
  companyStage: string;
};

type Verification = {
  date: string;
  score: number;
  percentile: number;
};

type Activity = {
  introductions: number;
  interviewsScheduled: number;
  avgResponseTime: string;
};

type DemandData = {
  introCount: number;
  days: number;
  isActive: boolean;
};

type ProfileData = {
  slug: string;
  userId: string;
  name: string;
  role?: string;
  experience?: string;
  location?: string;
  avatarUrl?: string;
  linkedinUrl?: string;
  resumeUrl?: string;
  githubUrl?: string;
  demandData?: DemandData;
  story?: string;
  strengths?: Strength[];
  proofOfWork?: ProofItem[];
  thoughts?: Thought[];
  opportunities?: Opportunities;
  verification?: Verification;
  activity?: Activity;
  introAudioUrl?: string;
  thinkingAudioUrl?: string;
};

const Index = () => {
  const { slug } = useParams<{ slug: string }>();

  const {
    data: profileData,
    isLoading,
    isError,
    error,
  } = useQuery<ProfileData>({
    queryKey: ["public-profile", slug],
    queryFn: async () => {
      if (!slug) {
        throw new Error("Missing slug");
      }
      // Call backend API hosted on api.relayy.world
      const apiUrl = `https://api.relayy.world/api/public/profiles/${slug}`;
      console.log(`[Profile] Fetching from: ${apiUrl}`);
      const res = await fetch(apiUrl);
      console.log(`[Profile] Response status: ${res.status} ${res.statusText}`);
      if (!res.ok) {
        const errorText = await res.text();
        console.error(`[Profile] API error: ${errorText}`);
        throw new Error(`Failed to load profile: ${res.status} ${res.statusText}`);
      }
      const data = await res.json();
      console.log(`[Profile] Loaded profile for: ${data.name || slug}`);
      console.log(`[Profile] introAudioUrl present:`, !!data.introAudioUrl);
      console.log(`[Profile] introAudioUrl length:`, data.introAudioUrl?.length || 0);
      console.log(`[Profile] thinkingAudioUrl present:`, !!data.thinkingAudioUrl);
      console.log(`[Profile] thinkingAudioUrl length:`, data.thinkingAudioUrl?.length || 0);
      return data;
    },
    enabled: !!slug,
  });

  if (!slug) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-background">
        <p className="text-muted-foreground">
          No profile specified. Please use a URL like <span className="font-mono">/saurabh</span>.
        </p>
      </div>
    );
  }

  if (isLoading || !profileData) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-background">
        <p className="text-muted-foreground">Loading profile...</p>
      </div>
    );
  }

  if (isError) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-background">
        <div className="text-center">
          <p className="text-muted-foreground mb-2">
            We couldn&apos;t find this profile. Please check the link.
          </p>
          {error && (
            <p className="text-sm text-muted-foreground mt-2">
              Error: {error instanceof Error ? error.message : String(error)}
            </p>
          )}
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-background">
      <div className="max-w-md sm:max-w-2xl mx-auto px-4 sm:px-6 py-8 sm:py-12">
        {/* Header / Profile section */}
        <ProfileHeader
          name={profileData.name}
          role={profileData.role}
          experience={profileData.experience}
          location={profileData.location}
          avatarUrl={profileData.avatarUrl}
          linkedinUrl={profileData.linkedinUrl}
          resumeUrl={profileData.resumeUrl}
          githubUrl={profileData.githubUrl}
          demandData={profileData.demandData}
          slug={slug}
          introAudioUrl={profileData.introAudioUrl}
          verificationScore={profileData.verification?.score}
          isAvailableToChat={profileData.demandData?.isActive}
        />

        {/* Basics / Skills / Links – match Momentum profile layout */}
        <ProfileBasics />
        <ProfileSkills
          skills={profileData.strengths?.map((strength) => strength.text)}
        />
        <ProfileLinks
          portfolioUrl={profileData.resumeUrl}
          linkedinUrl={profileData.linkedinUrl}
          githubUrl={profileData.githubUrl}
        />

        {/* Narrative sections – align with Momentum prompts */}
        <ProfileNarratives
          culture={profileData.story}
          proudProject={profileData.proofOfWork?.[0]?.description}
          idealRole={profileData.opportunities?.role}
        />

        {/* Strengths */}
        {profileData.strengths && profileData.strengths.length > 0 && (
          <section className="mt-12 animate-fade-in" style={{ animationDelay: "300ms" }}>
            <SectionLabel emoji="💪">What I'm best at</SectionLabel>
            <StrengthsList strengths={profileData.strengths} />
          </section>
        )}

        {/* Proof of Work */}
        {profileData.proofOfWork && profileData.proofOfWork.length > 0 && (
          <section className="mt-12 animate-fade-in" style={{ animationDelay: "400ms" }}>
            <SectionLabel emoji="🏆">Relevant experience</SectionLabel>
            <ProofOfWork items={profileData.proofOfWork} />
          </section>
        )}

        {/* Thoughts */}
        {profileData.thoughts && profileData.thoughts.length > 0 && (
          <section className="mt-12 animate-fade-in" style={{ animationDelay: "500ms" }}>
            <SectionLabel emoji="💭">How I think</SectionLabel>
            <div className="space-y-4">
              {profileData.thoughts.map((thought, index) => (
                <ThoughtCard key={index} content={thought.content} topic={thought.topic} />
              ))}
            </div>
          </section>
        )}

        {/* Ideal Opportunities */}
        {(profileData.opportunities?.role || profileData.opportunities?.industries?.length > 0 || profileData.opportunities?.companyStage) && (
          <section className="mt-12 animate-fade-in" style={{ animationDelay: "600ms" }}>
            <SectionLabel emoji="🎯">What I'm looking for</SectionLabel>
            <IdealOpportunities
              role={profileData.opportunities?.role}
              industries={profileData.opportunities?.industries || []}
              companyStage={profileData.opportunities?.companyStage}
            />
          </section>
        )}

        {/* Founder-Only Insights - Only show if thinkingAudioUrl exists */}
        {profileData.thinkingAudioUrl && (
          <section className="mt-12 animate-fade-in" style={{ animationDelay: "700ms" }}>
            <SectionLabel emoji="🔒">Founder-only insights</SectionLabel>
            <AudioPlayer
              title="How I make decisions"
              subtitle="2-minute deep dive on values & trade-offs"
              duration="2:00"
              src={profileData.thinkingAudioUrl}
            />
          </section>
        )}

        {/* Vance Verification Badge - Only show if verified (score > 0 or percentile > 0) */}
        {profileData.verification && (profileData.verification.score > 0 || profileData.verification.percentile > 0) && (
          <section className="mt-12 animate-fade-in" style={{ animationDelay: "800ms" }}>
            <VanceBadge
              verifiedDate={profileData.verification.date}
              score={profileData.verification.score}
              percentile={profileData.verification.percentile}
            />
          </section>
        )}

        {/* Vance Activity Card - Only show if there's activity */}
        {profileData.activity && (profileData.activity.introductions > 0 || profileData.activity.interviewsScheduled > 0 || profileData.activity.avgResponseTime) && (
          <section className="mt-6 animate-fade-in" style={{ animationDelay: "850ms" }}>
            <ActivityCard
              introductions={profileData.activity.introductions}
              interviewsScheduled={profileData.activity.interviewsScheduled}
              avgResponseTime={profileData.activity.avgResponseTime}
            />
          </section>
        )}

        {/* Footer */}
        <footer className="mt-16 pt-8 border-t border-border text-center animate-fade-in" style={{ animationDelay: "900ms" }}>
          <p className="text-sm text-muted-foreground">
            Powered by <span className="font-semibold text-foreground">Vance</span> · 
            Making hiring more human
          </p>
        </footer>
      </div>
    </div>
  );
};

export default Index;
