import { MapPin, Linkedin, FileText, Github } from "lucide-react";
import { useMemo, useState } from "react";

import { Button } from "@/components/ui/button";
import { Switch } from "@/components/ui/switch";
import { DemandBadge } from "./DemandBadge";
import { RequestIntroModal } from "./RequestIntroModal";
import { AudioPlayer } from "./AudioPlayer";

interface ProfileHeaderProps {
  name: string;
  role?: string;
  experience?: string;
  location?: string;
  avatarUrl?: string;
  linkedinUrl?: string;
  resumeUrl?: string;
  githubUrl?: string;
  demandData?: {
    introCount?: number;
    days?: number;
    isActive?: boolean;
  };
  slug?: string;
  introAudioUrl?: string;
  verificationScore?: number;
  isAvailableToChat?: boolean;
}

export const ProfileHeader = ({
  name,
  role,
  experience,
  location,
  avatarUrl,
  linkedinUrl,
  resumeUrl,
  githubUrl,
  demandData,
  slug,
  introAudioUrl,
  verificationScore,
  isAvailableToChat,
}: ProfileHeaderProps) => {
  const [showRequestIntro, setShowRequestIntro] = useState(false);

  const initials = useMemo(() => {
    if (!name) return "";
    const parts = name.trim().split(" ");
    if (parts.length === 1) {
      return parts[0][0]?.toUpperCase() ?? "";
    }
    return `${parts[0][0] ?? ""}${parts[1][0] ?? ""}`.toUpperCase();
  }, [name]);

  return (
    <header className="animate-fade-in" style={{ animationDelay: "0ms" }}>
      <div className="profile-card p-6 sm:p-8">
        <div className="flex flex-col gap-6">
          <div className="flex flex-col sm:flex-row sm:items-center gap-6">
            <div className="relative flex-shrink-0">
              <div className="h-24 w-24 sm:h-28 sm:w-28 rounded-full bg-secondary flex items-center justify-center text-3xl sm:text-4xl shadow-inner overflow-hidden">
                {avatarUrl ? (
                  <img src={avatarUrl} alt={name} className="h-full w-full object-cover" />
                ) : (
                  <span className="font-semibold text-foreground">{initials}</span>
                )}
              </div>
              {typeof verificationScore === "number" && verificationScore > 0 && (
                <div className="absolute -bottom-1 -right-1 h-8 w-8 rounded-full bg-primary text-background text-xs font-semibold flex items-center justify-center shadow-lg">
                  {verificationScore}
                </div>
              )}
            </div>
            <div className="flex-1">
              <h1 className="text-3xl sm:text-4xl font-serif text-foreground tracking-tight">
                {name}
              </h1>
              {(role || experience) && (
                <p className="mt-2 text-lg text-muted-foreground">
                  {[role, experience].filter(Boolean).join(" · ")}
                </p>
              )}
              {(location || linkedinUrl || resumeUrl || githubUrl) && (
                <div className="flex flex-wrap items-center gap-4 mt-2 text-muted-foreground">
                  {location && (
                    <div className="flex items-center gap-2">
                      <MapPin className="w-4 h-4" />
                      <span className="text-sm">{location}</span>
                    </div>
                  )}
                  {(linkedinUrl || resumeUrl || githubUrl) && (
                    <div className="flex items-center gap-2">
                      {linkedinUrl && (
                        <a
                          href={linkedinUrl}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="hover:text-primary transition-colors"
                        >
                          <Linkedin className="w-[17px] h-[17px]" />
                        </a>
                      )}
                      {resumeUrl && (
                        <a
                          href={resumeUrl}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="hover:text-primary transition-colors"
                        >
                          <FileText className="w-[17px] h-[17px]" />
                        </a>
                      )}
                      {githubUrl && (
                        <a
                          href={githubUrl}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="hover:text-primary transition-colors"
                        >
                          <Github className="w-[17px] h-[17px]" />
                        </a>
                      )}
                    </div>
                  )}
                </div>
              )}
              {demandData && (
                <div className="mt-3">
                  <DemandBadge
                    introCount={demandData.introCount}
                    days={demandData.days}
                    isActive={demandData.isActive}
                  />
                </div>
              )}
            </div>
            <Button
              className="sm:self-start gap-2"
              size="lg"
              onClick={() => setShowRequestIntro(true)}
            >
              Request intro
            </Button>
          </div>

          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 sm:gap-6 mt-2">
            {introAudioUrl && (
              <div className="w-full sm:max-w-md">
                <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground mb-1">
                  30-second intro
                </p>
                <AudioPlayer
                  title={`Hear how ${name.split(" ")[0]} explains their work`}
                  subtitle="30-second overview · Communication & thinking style"
                  duration="0:30"
                  src={introAudioUrl}
                />
              </div>
            )}
            <div className="flex items-center gap-3">
              <Switch
                checked={!!isAvailableToChat}
                disabled
                aria-label="Available to chat"
                className="data-[state=checked]:bg-emerald-500"
              />
              <div>
                <p className="text-sm font-medium text-foreground">Available to chat</p>
                <p className="text-xs text-muted-foreground">Founders can reach out</p>
              </div>
            </div>
          </div>
        </div>
      </div>

      <RequestIntroModal
        open={showRequestIntro}
        onOpenChange={setShowRequestIntro}
        candidateSlug={slug}
        candidateName={name}
      />
    </header>
  );
};