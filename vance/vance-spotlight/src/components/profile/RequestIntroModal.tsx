import { useState, useEffect } from "react";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Loader2, CheckCircle2, Phone, MessageCircle } from "lucide-react";

interface RequestIntroModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  candidateSlug: string;
  candidateName: string;
}

type RequestStatus =
  | "initial"
  | "checking"
  | "needs_info"
  | "needs_onboarding"
  | "call_initiated"
  | "call_completed"
  | "intro_requested"
  | "error";

export const RequestIntroModal = ({
  open,
  onOpenChange,
  candidateSlug,
  candidateName,
}: RequestIntroModalProps) => {
  const [countryCode, setCountryCode] = useState("+1");
  const [phoneNumber, setPhoneNumber] = useState("");
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [linkedinUrl, setLinkedinUrl] = useState("");
  const [status, setStatus] = useState<RequestStatus>("initial");
  const [error, setError] = useState("");
  const [whatsappLink, setWhatsappLink] = useState("https://shorturl.at/oxUJt");
  const [userId, setUserId] = useState("");

  // Poll for call completion if call was initiated
  useEffect(() => {
    if (status === "call_initiated" && userId) {
      const interval = setInterval(async () => {
        try {
          const response = await fetch(
            `https://api.relayy.world/api/public/profiles/${candidateSlug}/intro-status/${userId}`
          );
          if (response.ok) {
            const data = await response.json();
            if (data.call_status === "completed") {
              setStatus("call_completed");
              if (data.intro_requested) {
                // Always use fixed WhatsApp link
                setWhatsappLink("https://shorturl.at/oxUJt");
                setStatus("intro_requested");
              }
            }
          }
        } catch (err) {
          console.error("Error checking call status:", err);
        }
      }, 3000); // Check every 3 seconds

      return () => clearInterval(interval);
    }
  }, [status, userId, candidateSlug]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    
    // Validate all required fields
    if (!name || !email || !linkedinUrl || !phoneNumber) {
      setError("Please fill in all required fields");
      return;
    }
    
    // Combine country code and phone number
    const fullPhoneNumber = countryCode.replace(/\+/g, "") + phoneNumber.replace(/\D/g, "");
    
    setStatus("checking");

    try {
      const response = await fetch(
        `https://api.relayy.world/api/public/profiles/${candidateSlug}/request-intro`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            whatsapp_number: fullPhoneNumber,
            country_code: countryCode,
            name: name,
            email: email,
            linkedin_url: linkedinUrl,
          }),
        }
      );

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || "Failed to request intro");
      }

      const data = await response.json();

      if (data.status === "intro_requested") {
        // Existing user, intro already sent
        setStatus("intro_requested");
        // Always use fixed WhatsApp link
        setWhatsappLink("https://shorturl.at/oxUJt");
      } else if (data.status === "call_initiated") {
        // New user, call initiated
        setStatus("call_initiated");
        setUserId(data.user_id);
        // Set fixed WhatsApp link for after call completion
        setWhatsappLink("https://shorturl.at/oxUJt");
      } else {
        setStatus("error");
        setError(data.message || "Unexpected response from server");
      }
    } catch (err) {
      setStatus("error");
      setError(err instanceof Error ? err.message : "An error occurred");
    }
  };


  const resetForm = () => {
    setCountryCode("+1");
    setPhoneNumber("");
    setName("");
    setEmail("");
    setLinkedinUrl("");
    setStatus("initial");
    setError("");
    setWhatsappLink("https://shorturl.at/oxUJt");
    setUserId("");
  };

  return (
    <Dialog open={open} onOpenChange={(open) => {
      if (!open) {
        resetForm();
      }
      onOpenChange(open);
    }}>
      <DialogContent className="sm:max-w-[500px]">
        <DialogHeader>
          <DialogTitle>Request Intro to {candidateName}</DialogTitle>
          <DialogDescription>
            {status === "initial" && "Enter your details to request an intro"}
            {status === "call_initiated" && "Answer the incoming call to complete onboarding"}
            {status === "call_completed" && "Call completed! Processing your intro request..."}
            {status === "intro_requested" && "Intro request sent! Connect with Vance on WhatsApp"}
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4 py-4">
          {status === "initial" && (
            <form onSubmit={handleSubmit} className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="name">Full Name *</Label>
                <Input
                  id="name"
                  type="text"
                  placeholder="John Doe"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  required
                />
              </div>
              
              <div className="space-y-2">
                <Label htmlFor="email">Email *</Label>
                <Input
                  id="email"
                  type="email"
                  placeholder="john@example.com"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  required
                />
              </div>
              
              <div className="space-y-2">
                <Label htmlFor="linkedin">LinkedIn URL *</Label>
                <Input
                  id="linkedin"
                  type="url"
                  placeholder="https://linkedin.com/in/johndoe"
                  value={linkedinUrl}
                  onChange={(e) => setLinkedinUrl(e.target.value)}
                  required
                />
              </div>
              
              <div className="grid grid-cols-3 gap-2">
                <div className="space-y-2">
                  <Label htmlFor="countryCode">Country Code *</Label>
                  <Input
                    id="countryCode"
                    type="text"
                    placeholder="+1"
                    value={countryCode}
                    onChange={(e) => setCountryCode(e.target.value)}
                    required
                    className="text-sm"
                  />
                </div>
                <div className="col-span-2 space-y-2">
                  <Label htmlFor="phoneNumber">Phone Number *</Label>
                  <Input
                    id="phoneNumber"
                    type="tel"
                    placeholder="1234567890"
                    value={phoneNumber}
                    onChange={(e) => setPhoneNumber(e.target.value.replace(/\D/g, ""))}
                    required
                  />
                </div>
              </div>
              
              {error && (
                <p className="text-sm text-destructive">{error}</p>
              )}
              
              <Button type="submit" className="w-full" disabled={status === "checking"}>
                {status === "checking" ? (
                  <>
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    Checking...
                  </>
                ) : (
                  "Request Intro"
                )}
              </Button>
            </form>
          )}


          {status === "call_initiated" && (
            <div className="space-y-4 text-center">
              <div className="flex justify-center">
                <Phone className="h-16 w-16 text-primary animate-pulse" />
              </div>
              <div>
                <h3 className="font-semibold mb-2">Incoming Call</h3>
                <p className="text-sm text-muted-foreground">
                  Please answer the call from Vance to complete your onboarding.
                  We'll notify you once your intro request is sent.
                </p>
              </div>
              <div className="flex items-center justify-center gap-2 text-sm text-muted-foreground">
                <Loader2 className="h-4 w-4 animate-spin" />
                <span>Waiting for call to complete...</span>
              </div>
            </div>
          )}

          {status === "call_completed" && (
            <div className="space-y-4 text-center">
              <div className="flex justify-center">
                <Loader2 className="h-16 w-16 text-primary animate-spin" />
              </div>
              <p className="text-sm text-muted-foreground">
                Processing your intro request...
              </p>
            </div>
          )}

          {status === "intro_requested" && (
            <div className="space-y-4 text-center">
              <div className="flex justify-center">
                <CheckCircle2 className="h-16 w-16 text-green-500" />
              </div>
              <div>
                <h3 className="font-semibold mb-2">Intro Request Sent!</h3>
                <p className="text-sm text-muted-foreground mb-4">
                  Your intro request has been sent to {candidateName}.
                  Click the button below to talk to Vance on WhatsApp.
                </p>
              </div>
              {whatsappLink && (
                <Button
                  asChild
                  className="w-full"
                  size="lg"
                >
                  <a
                    href={whatsappLink}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="flex items-center justify-center gap-2"
                  >
                    <MessageCircle className="h-5 w-5" />
                    Talk to Vance on WhatsApp
                  </a>
                </Button>
              )}
            </div>
          )}

          {status === "error" && (
            <div className="space-y-4">
              <p className="text-sm text-destructive">{error}</p>
              <Button
                onClick={() => {
                  resetForm();
                  setStatus("initial");
                }}
                variant="outline"
                className="w-full"
              >
                Try Again
              </Button>
            </div>
          )}
        </div>
      </DialogContent>
    </Dialog>
  );
};

