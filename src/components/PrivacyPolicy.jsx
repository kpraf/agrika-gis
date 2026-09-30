import React from "react";
import Navbar from "./layout/Navbar";
import Footer from "./layout/Footer";

const LAST_UPDATED = "September 27, 2026";

function Section({ title, children }) {
  return (
    <section className="flex flex-col gap-3">
      <h2 className="text-xl md:text-2xl font-bold text-[#1B3315]">{title}</h2>
      <div className="flex flex-col gap-3 text-[15px] leading-7 text-[#4B5563]">{children}</div>
    </section>
  );
}

export default function PrivacyPolicy() {
  return (
    <div className="w-full bg-white font-sans" style={{ fontFamily: "'Plus Jakarta Sans', sans-serif" }}>
      {/* Hero + Nav */}
      <section className="relative bg-[#0B2005] overflow-hidden min-h-[500px] flex flex-col">
        <div className="absolute inset-0 bg-[url('/images/farms.png')] bg-cover bg-center" />
        <div className="absolute inset-0 bg-[#153321]/45" />

        <Navbar active="" />

        <div className="relative z-10 flex-1 flex flex-col items-start justify-center gap-4 px-6 md:px-12 pb-12 max-w-4xl">
          <h1 className="text-4xl md:text-6xl font-extrabold text-white leading-[1.05]">
            Privacy Policy
          </h1>
          <p className="text-lg md:text-xl text-[#E5E7EB] max-w-2xl">
            How AgriKA-GIS collects, uses, and protects the information you share when using the
            platform.
          </p>
          <p className="text-[#CBD5C0] text-sm">Last updated: {LAST_UPDATED}</p>
        </div>
      </section>

      {/* Content */}
      <section className="bg-white py-14 px-6 md:px-16 flex justify-center">
        <div className="max-w-3xl w-full flex flex-col gap-10">
          <p className="text-[15px] leading-7 text-[#4B5563]">
            AgriKA-GIS is a web based rice yield forecasting and GIS monitoring platform developed as
            an undergraduate research project for the province of Laguna, Philippines. This Privacy
            Policy explains what information the platform collects, how it is used, and the choices you
            have. By using AgriKA-GIS, you agree to the practices described here.
          </p>

          <Section title="1. Information We Collect">
            <p>We keep data collection to the minimum needed to run the platform:</p>
            <ul className="list-disc pl-5 flex flex-col gap-1.5">
              <li>
                <b>Portal account information.</b> For authorized users (administrators,
                agriculturists, and rice technicians), we store a username, full name, assigned role,
                assigned municipality, and a securely hashed password. We never store passwords in
                plain text.
              </li>
              <li>
                <b>Contact form details.</b> If you send a message through the Contact page, we receive
                the name, organization, phone number, subject, and message you provide.
              </li>
              <li>
                <b>Technical information.</b> Like most websites, our servers may record standard
                request logs such as the pages requested and general error information, used only to
                keep the service running and secure.
              </li>
            </ul>
            <p>
              The public Yield Map and dashboards can be viewed without an account and do not require
              you to submit personal information.
            </p>
          </Section>

          <Section title="2. How We Use Information">
            <ul className="list-disc pl-5 flex flex-col gap-1.5">
              <li>To operate the platform and display rice yield, boundary, and environmental data.</li>
              <li>To authenticate portal users and apply the correct role and municipality scope.</li>
              <li>To respond to inquiries submitted through the Contact page.</li>
              <li>To maintain the security, reliability, and academic goals of the research project.</li>
            </ul>
          </Section>

          <Section title="3. Data Sources and Third Party Services">
            <p>
              AgriKA-GIS combines publicly available data and third party services to power the map and
              forecasts. These include map basemaps and tiles, weather and climate data, and satellite
              imagery, along with hosting and database providers. These services process map and data
              requests, not your personal account information, and each operates under its own terms and
              privacy practices.
            </p>
          </Section>

          <Section title="4. How We Share Information">
            <p>
              We do not sell your personal information. Portal account details are accessible only to
              the project team and to authorized administrators managing accounts within the platform.
              We may disclose information if required to do so by law or to protect the safety and
              integrity of the service.
            </p>
          </Section>

          <Section title="5. Data Retention">
            <p>
              Account information is retained for as long as the account remains active or as needed for
              the research project. Contact messages are kept only as long as needed to address your
              inquiry. You may request removal of your information as described below.
            </p>
          </Section>

          <Section title="6. Security">
            <p>
              Passwords are stored using industry standard hashing, and access to the portal is
              protected by authenticated sessions. While we take reasonable steps to safeguard data, no
              method of transmission or storage is completely secure, and we cannot guarantee absolute
              security.
            </p>
          </Section>

          <Section title="7. Your Choices and Rights">
            <p>
              You may request access to, correction of, or deletion of the personal information we hold
              about you. Portal users can also have their accounts updated or deactivated by an
              administrator. To make a request, please reach out through the Contact page.
            </p>
          </Section>

          <Section title="8. Children's Privacy">
            <p>
              AgriKA-GIS is intended for local government units, agricultural offices, researchers, and
              the general public. It is not directed to children, and we do not knowingly collect
              personal information from children.
            </p>
          </Section>

          <Section title="9. Changes to This Policy">
            <p>
              We may update this Privacy Policy as the platform evolves. When we do, we will revise the
              date shown at the top of this page. Continued use of AgriKA-GIS after changes take effect
              means you accept the updated policy.
            </p>
          </Section>

          <Section title="10. Contact Us">
            <p>
              If you have questions about this Privacy Policy or how your information is handled, please
              use the Contact page on this site to reach the AgriKA-GIS team.
            </p>
          </Section>
        </div>
      </section>

      <Footer />
    </div>
  );
}
