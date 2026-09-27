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

export default function TermsOfService() {
  return (
    <div className="w-full bg-white font-sans" style={{ fontFamily: "'Plus Jakarta Sans', sans-serif" }}>
      {/* Hero + Nav */}
      <section className="relative bg-[#0B2005] overflow-hidden flex flex-col">
        <Navbar active="" />
        <div className="relative z-10 px-6 md:px-12 pt-6 pb-14 max-w-4xl">
          <h1 className="text-4xl md:text-5xl font-extrabold text-white leading-[1.1]">Terms of Service</h1>
          <p className="mt-3 text-[#CBD5C0] text-sm">Last updated: {LAST_UPDATED}</p>
        </div>
      </section>

      {/* Content */}
      <section className="bg-white py-14 px-6 md:px-16 flex justify-center">
        <div className="max-w-3xl w-full flex flex-col gap-10">
          <p className="text-[15px] leading-7 text-[#4B5563]">
            These Terms of Service govern your use of AgriKA-GIS, a web based rice yield forecasting and
            GIS monitoring platform developed as an undergraduate research project for the province of
            Laguna, Philippines. By accessing or using the platform, you agree to these terms. If you do
            not agree, please do not use the service.
          </p>

          <Section title="1. Description of the Service">
            <p>
              AgriKA-GIS provides an interactive map, dashboards, and analytics that present rice yield
              estimates and related environmental data. It includes a public Yield Map that anyone can
              view, and a secured portal for authorized local government and agriculture office users.
              The platform is offered for informational, research, and educational purposes.
            </p>
          </Section>

          <Section title="2. Accounts and Access">
            <p>
              Portal accounts are issued to authorized users only, with roles such as administrator,
              agriculturist, and rice technician. If you are given an account, you are responsible for
              keeping your credentials confidential and for activity performed under your account.
              Notify an administrator promptly if you believe your account has been compromised.
            </p>
          </Section>

          <Section title="3. Acceptable Use">
            <p>You agree not to:</p>
            <ul className="list-disc pl-5 flex flex-col gap-1.5">
              <li>Attempt to gain unauthorized access to any part of the platform or its data.</li>
              <li>Interfere with, disrupt, or place undue load on the service or its infrastructure.</li>
              <li>Upload false or misleading data through any import feature.</li>
              <li>Use the platform for any unlawful purpose or in violation of these terms.</li>
            </ul>
          </Section>

          <Section title="4. Data Accuracy and Disclaimer">
            <p>
              Yield values shown on AgriKA-GIS include historical records as well as estimates and
              forecasts produced by predictive models. These figures may contain errors and should not
              be treated as guaranteed or official results. During development, some areas may display
              sample or placeholder data. Always confirm with the relevant agriculture office before
              relying on any figure for operational or financial decisions.
            </p>
          </Section>

          <Section title="5. Intellectual Property">
            <p>
              The AgriKA-GIS platform, including its design, code, and original content, belongs to the
              project team. Boundary, weather, satellite, and basemap data are provided by their
              respective sources and remain subject to the licenses and terms of those providers.
            </p>
          </Section>

          <Section title="6. Third Party Services">
            <p>
              The platform relies on third party providers for map tiles, weather and climate data,
              satellite imagery, hosting, and databases. We are not responsible for the availability,
              accuracy, or practices of these third party services, which operate under their own terms.
            </p>
          </Section>

          <Section title="7. Disclaimer of Warranties">
            <p>
              The service is provided on an as is and as available basis, without warranties of any
              kind, whether express or implied. We do not warrant that the platform will be
              uninterrupted, error free, or that any data will be accurate or complete.
            </p>
          </Section>

          <Section title="8. Limitation of Liability">
            <p>
              To the fullest extent permitted by law, the AgriKA-GIS team shall not be liable for any
              indirect, incidental, or consequential damages, or for any loss arising from your use of
              or reliance on the platform or its data.
            </p>
          </Section>

          <Section title="9. Changes to the Service and Terms">
            <p>
              As a research project, AgriKA-GIS may change, add, or remove features at any time. We may
              also update these terms, and when we do we will revise the date shown at the top of this
              page. Continued use after changes take effect means you accept the updated terms.
            </p>
          </Section>

          <Section title="10. Governing Law">
            <p>
              These terms are governed by the laws of the Republic of the Philippines, without regard to
              conflict of law principles.
            </p>
          </Section>

          <Section title="11. Contact Us">
            <p>
              If you have questions about these Terms of Service, please use the Contact page on this
              site to reach the AgriKA-GIS team.
            </p>
          </Section>
        </div>
      </section>

      <Footer />
    </div>
  );
}
