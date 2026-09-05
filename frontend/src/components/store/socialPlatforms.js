import { Globe, Mail, MessageCircle, Phone } from "lucide-react";

import {
  FacebookIcon,
  InstagramIcon,
  TiktokIcon,
} from "./socialIcons";

/**
 * The platforms a store can list, in the order both interfaces show them.
 *
 * Must stay in step with PLATFORMS in app/models/store_social_link.py, which
 * is what the CHECK constraint and the service validate against — this list
 * only decides order, icon and label.
 *
 * `hint` is the example placed in the vendor field. It shows the loosest
 * form the server accepts, not the canonical one, because the point of the
 * field is that a vendor may paste whatever they have.
 */
export const SOCIAL_PLATFORMS = [
  { id: "instagram", Icon: InstagramIcon, hint: "@hamragrocery" },
  { id: "facebook", Icon: FacebookIcon, hint: "facebook.com/HamraGrocery" },
  { id: "tiktok", Icon: TiktokIcon, hint: "@hamragrocery" },
  { id: "whatsapp", Icon: MessageCircle, hint: "+961 3 123 456" },
  { id: "website", Icon: Globe, hint: "hamragrocery.com" },
  { id: "email", Icon: Mail, hint: "hello@hamragrocery.com" },
  { id: "phone", Icon: Phone, hint: "+961 1 340 000" },
];

export const PLATFORM_IDS = SOCIAL_PLATFORMS.map((platform) => platform.id);
