import {
  User,
  MapPin,
  LockKeyhole,
  CreditCard,
  ShoppingBag,
  Bell,
  ShieldCheck,
  ChevronRight,
  Languages,
  Coins,
} from "lucide-react";
import { Link } from "react-router-dom";
import { useTranslation } from "react-i18next";

function Settings() {
  const { t } = useTranslation();

  const settingSections = [
    {
      title: t("settings.accountProfile.title"),
      description: t("settings.accountProfile.description"),
      items: [
        {
          icon: User,
          title: t("settings.personalInformation.title"),
          description: t("settings.personalInformation.description"),
          path: "/profile",
        },
        {
          icon: MapPin,
          title: t("settings.savedAddresses.title"),
          description: t("settings.savedAddresses.description"),
          path: "/settings/addresses",
        },
        {
          icon: LockKeyhole,
          title: t("settings.loginSecurity.title"),
          description: t("settings.loginSecurity.description"),
          path: "/settings/security",
        },
        {
          icon: Languages,
          title: t("settings.language.title"),
          description: t("settings.language.description"),
          path: "/settings/language",
        },
      ],
    },
    {
      title: t("settings.shoppingOrders.title"),
      description: t("settings.shoppingOrders.description"),
      items: [
        {
          icon: CreditCard,
          title: t("settings.paymentMethods.title"),
          description: t("settings.paymentMethods.description"),
          path: "/settings/payment-methods",
        },
        {
          icon: Coins,
          title: t("settings.currency.title"),
          description: t("settings.currency.description"),
          path: "/settings/currency",
        },
        {
          icon: ShoppingBag,
          title: t("settings.shoppingPreferences.title"),
          description: t("settings.shoppingPreferences.description"),
          path: "/settings/shopping",
        },
      ],
    },
    {
      title: t("settings.notifications.title"),
      description: t("settings.notifications.description"),
      items: [
        {
          icon: Bell,
          title: t("settings.notificationPreferences.title"),
          description: t(
            "settings.notificationPreferences.description",
          ),
          path: "/settings/notifications",
        },
      ],
    },
    {
      title: t("settings.privacyData.title"),
      description: t("settings.privacyData.description"),
      items: [
        {
          icon: ShieldCheck,
          title: t("settings.privacyData.title"),
          description: t("settings.privacyData.itemDescription"),
          path: "/settings/privacy",
        },
      ],
    },
  ];

  return (
    <div className="min-h-[70vh] bg-gray-50 px-6 py-10">
      <div className="mx-auto max-w-4xl">
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-gray-900">
            {t("settings.title")}
          </h1>

          <p className="mt-2 text-gray-600">
            {t("settings.subtitle")}
          </p>
        </div>

        {/* Settings Sections */}
        <div className="space-y-6">
          {settingSections.map((section) => (
            <section
              key={section.title}
              className="overflow-hidden rounded-2xl bg-white shadow-sm"
            >
              {/* Section Header */}
              <div className="border-b border-gray-100 px-6 py-5">
                <h2 className="text-xl font-semibold text-gray-900">
                  {section.title}
                </h2>

                <p className="mt-1 text-sm text-gray-500">
                  {section.description}
                </p>
              </div>

              {/* Section Items */}
              <div>
                {section.items.map((item, index) => {
                  const Icon = item.icon;

                  return (
                    <Link
                      key={item.title}
                      to={item.path}
                      className={`group flex items-center gap-4 px-6 py-5 transition hover:bg-gray-50 ${
                        index !== section.items.length - 1
                          ? "border-b border-gray-100"
                          : ""
                      }`}
                    >
                      {/* Icon */}
                      <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-emerald-50 text-emerald-700">
                        <Icon size={21} />
                      </div>

                      {/* Text */}
                      <div className="min-w-0 flex-1">
                        <h3 className="font-medium text-gray-900 group-hover:text-emerald-700">
                          {item.title}
                        </h3>

                        <p className="mt-1 text-sm text-gray-500">
                          {item.description}
                        </p>
                      </div>

                      {/* Arrow — points toward the row's trailing edge */}
                      <ChevronRight
                        size={20}
                        className="shrink-0 text-gray-400 transition group-hover:translate-x-1 group-hover:text-emerald-700 rtl:rotate-180"
                      />
                    </Link>
                  );
                })}
              </div>
            </section>
          ))}
        </div>
      </div>
    </div>
  );
}

export default Settings;