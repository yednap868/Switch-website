import { Globe2, Linkedin, Github, Twitter } from "lucide-react";
import { Button } from "@/components/ui/button";

export interface ProfileLinksProps {
  portfolioUrl?: string;
  linkedinUrl?: string;
  githubUrl?: string;
  twitterHandle?: string;
}

const formatDomain = (url?: string) => {
  if (!url) return "";
  try {
    const parsed = new URL(url);
    return parsed.host.replace(/^www\./, "") + parsed.pathname.replace(/\/$/, "");
  } catch {
    return url.replace(/^https?:\/\//, "");
  }
};

export const ProfileLinks = ({
  portfolioUrl,
  linkedinUrl,
  githubUrl,
  twitterHandle,
}: ProfileLinksProps) => {
  return (
    <section className="mt-8 animate-fade-in" style={{ animationDelay: "220ms" }}>
      <div className="flex items-center justify-between mb-3">
        <h2 className="text-lg font-semibold">Links</h2>
        <Button variant="ghost" size="sm" className="gap-1 text-xs font-medium">
          + Add
        </Button>
      </div>
      <div className="profile-card divide-y divide-border">
        {portfolioUrl && (
          <LinkRow
            icon={<Globe2 className="h-4 w-4" />}
            label="Portfolio"
            value={formatDomain(portfolioUrl)}
            href={portfolioUrl}
          />
        )}
        {linkedinUrl && (
          <LinkRow
            icon={<Linkedin className="h-4 w-4" />}
            label="LinkedIn"
            value={formatDomain(linkedinUrl)}
            href={linkedinUrl}
          />
        )}
        {githubUrl && (
          <LinkRow
            icon={<Github className="h-4 w-4" />}
            label="GitHub"
            value={formatDomain(githubUrl)}
            href={githubUrl}
          />
        )}
        {twitterHandle && (
          <LinkRow
            icon={<Twitter className="h-4 w-4" />}
            label="X (Twitter)"
            value={twitterHandle.startsWith("@") ? twitterHandle : `@${twitterHandle}`}
            href={twitterHandle.startsWith("http") ? twitterHandle : `https://x.com/${twitterHandle.replace(/^@/, "")}`}
          />
        )}
      </div>
    </section>
  );
};

interface LinkRowProps {
  icon: React.ReactNode;
  label: string;
  value: string;
  href: string;
}

const LinkRow = ({ icon, label, value, href }: LinkRowProps) => {
  return (
    <a
      href={href}
      target="_blank"
      rel="noopener noreferrer"
      className="flex items-center justify-between px-4 py-3 sm:px-5 sm:py-4 hover:bg-muted/40 transition-colors"
    >
      <div className="flex items-center gap-3">
        <span className="inline-flex h-8 w-8 items-center justify-center rounded-full bg-secondary text-foreground">
          {icon}
        </span>
        <div>
          <p className="text-sm font-medium text-foreground">{label}</p>
          <p className="text-sm text-accent underline underline-offset-2">{value}</p>
        </div>
      </div>
    </a>
  );
};



