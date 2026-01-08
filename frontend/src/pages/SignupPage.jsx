import "./SignupPage.css";
import Modal from "../components/Modal";
import { useMemo, useState } from "react";

function SignupPage() {
    const categories = useMemo(
        () => [
            {
                id: "allergy",
                label: "allergy (Required)",
                options: Array.from({ length: 14}, (_, i) => ({
                    id: `allergy-${i +1}`,
                    label: `Allergy Option ${i +1}`
                })),
            },
            {
                id:"dislike",
                label: "Dislike (Optional)",
                options: Array.from({ length: 14 }, (_, i) => ({
                    id: `dislike-${i + 1}`,
                    label: `Dislike Option ${i + 1}`,
        })),
            }
        ],
        []
    );

    const [isModalOpen, setIsModalOpen] = useState(false);
    const [modalType, setModalType] = useState(null);
    
    const openModal = (type) => {
      setModalType(type);
      setIsModalOpen(true);
    }

    /*버튼 이벤트 핸들러*/ 
    function handleSignup() {
      console.log("Sign up Complite");
      setIsModalOpen(false)
    };

    function handleCancel() {
      console.log("Cancel Complite");
      setIsModalOpen(false)
    };

    // 카테고리 클릭 전엔 옵션이 안 나오게: 초기값을 "" 로 둠
    const [activeCategoryId, setActiveCategoryId] = useState("");

    // 카테고리별 체크 상태 유지
    const [selections, setSelections] = useState(() => {
        const init = {};
        categories.forEach((c) => (init[c.id] = []));
        return init;
    });

    const activeCategory = categories.find((c) => c.id === activeCategoryId) || null;
    const checkedList = activeCategoryId ? selections[activeCategoryId] ?? [] : [];

    const onClickCategory = (categoryId) => {
        // 같은 카테고리 버튼을 다시 누르면 접히게(원치 않으면 이 if 블록 지우면 됨)
        setActiveCategoryId((prev) => (prev === categoryId ? "" : categoryId));
    };

    const toggleOption = (optionId) => {
        if (!activeCategoryId) return;

        setSelections((prev) => {
        const current = prev[activeCategoryId] ?? [];
        const exists = current.includes(optionId);

        return {
            ...prev,
            [activeCategoryId]: exists
            ? current.filter((id) => id !== optionId)
            : [...current, optionId],
        };
        });
    };

  return (
    <div>
        <section>
            Create your account
        </section>
        
        <section>
            <label>
            E-mail
                <input
                    name="email"
                    type="text"
                    placeholder="example@email.com"
                    maxLength={30}
                />
            </label>

            <label>
            Nickname
            <input
                name="nickname"
                type="text"
                placeholder="No more than 10 letters"
                maxLength={10}
            />
            </label>

            <label>
            Password
            <input
                name="password"
                type="password"
                placeholder="Not more than 8 to 20 letters"
                maxLength={20}
            />
            </label>

            <label>
            Password Check
            <input
                name="passwordConfirm"
                type="password"
                placeholder="check password"
                maxLength={20}
            />
            </label>
{/* 성별 선택창 */}
            <label>
            Gender
                <select name="gender">
                    <option value="">choose</option>
                    <option value="Man">Man</option>
                    <option value="Woman">Woman</option>
                    <option value="Unknown">Not select</option>
                </select>
            </label>
{/* 국가선택창 */}
            <label>
            Nationality
                <select
                    id="defaultPhysicalAddress.countryCode"
                    name="defaultPhysicalAddress.countryCode"
                >
                    <option value="">Choose your country</option>
                    <option value="US">United States</option>
                    <option value="AF">Afghanistan</option>
                    <option value="AX">Aland Islands</option>
                    <option value="AL">Albania</option>
                    <option value="DZ">Algeria</option>
                    <option value="AS">American Samoa</option>
                    <option value="AD">Andorra</option>
                    <option value="AO">Angola</option>
                    <option value="AI">Anguilla</option>
                    <option value="AQ">Antarctica</option>
                    <option value="AG">Antigua and Barbuda</option>
                    <option value="AR">Argentina</option>
                    <option value="AM">Armenia</option>
                    <option value="AW">Aruba</option>
                    <option value="AU">Australia</option>
                    <option value="AT">Austria</option>
                    <option value="AZ">Azerbaijan</option>
                    <option value="BS">Bahamas</option>
                    <option value="BH">Bahrain</option>
                    <option value="BD">Bangladesh</option>
                    <option value="BB">Barbados</option>
                    <option value="BE">Belgium</option>
                    <option value="BZ">Belize</option>
                    <option value="BJ">Benin</option>
                    <option value="BM">Bermuda</option>
                    <option value="BT">Bhutan</option>
                    <option value="BO">Bolivia</option>
                    <option value="BA">Bosnia and Herzegovina</option>
                    <option value="BW">Botswana</option>
                    <option value="BV">Bouvet Island</option>
                    <option value="BR">Brazil</option>
                    <option value="IO">British Indian Ocean Territory</option>
                    <option value="BN">Brunei Darussalam</option>
                    <option value="BG">Bulgaria</option>
                    <option value="BF">Burkina Faso</option>
                    <option value="BI">Burundi</option>
                    <option value="KH">Cambodia</option>
                    <option value="CM">Cameroon</option>
                    <option value="CA">Canada</option>
                    <option value="CV">Cape Verde</option>
                    <option value="KY">Cayman Islands</option>
                    <option value="CF">Central African Republic</option>
                    <option value="TD">Chad</option>
                    <option value="CL">Chile</option>
                    <option value="CN">China</option>
                    <option value="CX">Christmas Island</option>
                    <option value="CC">Cocos (Keeling) Islands</option>
                    <option value="CO">Colombia</option>
                    <option value="KM">Comoros</option>
                    <option value="CG">Congo</option>
                    <option value="CD">Congo, The Democratic Republic of the</option>
                    <option value="CK">Cook Islands</option>
                    <option value="CR">Costa Rica</option>
                    <option value="CI">Cote d'Ivoire</option>
                    <option value="HR">Croatia</option>
                    <option value="CY">Cyprus</option>
                    <option value="CZ">Czech Republic</option>
                    <option value="DK">Denmark</option>
                    <option value="DJ">Djibouti</option>
                    <option value="DM">Dominica</option>
                    <option value="DO">Dominican Republic</option>
                    <option value="EC">Ecuador</option>
                    <option value="EG">Egypt</option>
                    <option value="SV">El Salvador</option>
                    <option value="GQ">Equatorial Guinea</option>
                    <option value="ER">Eritrea</option>
                    <option value="EE">Estonia</option>
                    <option value="ET">Ethiopia</option>
                    <option value="FK">Falkland Islands (Malvinas)</option>
                    <option value="FO">Faroe Islands</option>
                    <option value="FJ">Fiji</option>
                    <option value="FI">Finland</option>
                    <option value="FR">France</option>
                    <option value="GF">French Guiana</option>
                    <option value="PF">French Polynesia</option>
                    <option value="TF">French Southern Territories</option>
                    <option value="GA">Gabon</option>
                    <option value="GM">Gambia</option>
                    <option value="GE">Georgia</option>
                    <option value="DE">Germany</option>
                    <option value="GH">Ghana</option>
                    <option value="GI">Gibraltar</option>
                    <option value="GR">Greece</option>
                    <option value="GL">Greenland</option>
                    <option value="GD">Grenada</option>
                    <option value="GP">Guadeloupe</option>
                    <option value="GU">Guam</option>
                    <option value="GT">Guatemala</option>
                    <option value="GN">Guinea</option>
                    <option value="GW">Guinea-Bissau</option>
                    <option value="GY">Guyana</option>
                    <option value="HT">Haiti</option>
                    <option value="HM">Heard Island and McDonald Islands</option>
                    <option value="HN">Honduras</option>
                    <option value="HK">Hong Kong</option>
                    <option value="HU">Hungary</option>
                    <option value="IS">Iceland</option>
                    <option value="IN">India</option>
                    <option value="ID">Indonesia</option>
                    <option value="IQ">Iraq</option>
                    <option value="IE">Ireland</option>
                    <option value="IL">Israel</option>
                    <option value="IT">Italy</option>
                    <option value="JM">Jamaica</option>
                    <option value="JP">Japan</option>
                    <option value="JO">Jordan</option>
                    <option value="KZ">Kazakhstan</option>
                    <option value="KE">Kenya</option>
                    <option value="KI">Kiribati</option>
                    <option value="KW">Kuwait</option>
                    <option value="KG">Kyrgyzstan</option>
                    <option value="LA">Lao People's Democratic Republic</option>
                    <option value="LV">Latvia</option>
                    <option value="LB">Lebanon</option>
                    <option value="LS">Lesotho</option>
                    <option value="LR">Liberia</option>
                    <option value="LY">Libya</option>
                    <option value="LI">Liechtenstein</option>
                    <option value="LT">Lithuania</option>
                    <option value="LU">Luxembourg</option>
                    <option value="MO">Macau</option>
                    <option value="MK">Macedonia</option>
                    <option value="MG">Madagascar</option>
                    <option value="MW">Malawi</option>
                    <option value="MY">Malaysia</option>
                    <option value="MV">Maldives</option>
                    <option value="ML">Mali</option>
                    <option value="MT">Malta</option>
                    <option value="MH">Marshall Islands</option>
                    <option value="MQ">Martinique</option>
                    <option value="MR">Mauritania</option>
                    <option value="MU">Mauritius</option>
                    <option value="YT">Mayotte</option>
                    <option value="MX">Mexico</option>
                    <option value="FM">Micronesia (Federated States of)</option>
                    <option value="MD">Moldova, Republic of</option>
                    <option value="MC">Monaco</option>
                    <option value="MN">Mongolia</option>
                    <option value="ME">Montenegro</option>
                    <option value="MS">Montserrat</option>
                    <option value="MA">Morocco</option>
                    <option value="MZ">Mozambique</option>
                    <option value="MM">Myanmar</option>
                    <option value="NA">Namibia</option>
                    <option value="NR">Nauru</option>
                    <option value="NP">Nepal</option>
                    <option value="NL">Netherlands</option>
                    <option value="AN">Netherlands Antilles</option>
                    <option value="NC">New Caledonia</option>
                    <option value="NZ">New Zealand</option>
                    <option value="NI">Nicaragua</option>
                    <option value="NE">Niger</option>
                    <option value="NG">Nigeria</option>
                    <option value="NU">Niue</option>
                    <option value="NF">Norfolk Island</option>
                    <option value="MP">Northern Mariana Islands</option>
                    <option value="NO">Norway</option>
                    <option value="OM">Oman</option>
                    <option value="PK">Pakistan</option>
                    <option value="PW">Palau</option>
                    <option value="PA">Panama</option>
                    <option value="PG">Papua New Guinea</option>
                    <option value="PY">Paraguay</option>
                    <option value="PE">Peru</option>
                    <option value="PH">Philippines</option>
                    <option value="PN">Pitcairn</option>
                    <option value="PL">Poland</option>
                    <option value="PT">Portugal</option>
                    <option value="PR">Puerto Rico</option>
                    <option value="QA">Qatar</option>
                    <option value="RE">Reunion</option>
                    <option value="RO">Romania</option>
                    <option value="RW">Rwanda</option>
                    <option value="SH">Saint Helena</option>
                    <option value="KN">Saint Kitts and Nevis</option>
                    <option value="LC">Saint Lucia</option>
                    <option value="PM">Saint Pierre and Miquelon</option>
                    <option value="VC">Saint Vincent and the Grenadines</option>
                    <option value="WS">Samoa</option>
                    <option value="SM">San Marino</option>
                    <option value="ST">Sao Tome and Principe</option>
                    <option value="SA">Saudi Arabia</option>
                    <option value="SN">Senegal</option>
                    <option value="RS">Serbia</option>
                    <option value="SC">Seychelles</option>
                    <option value="SL">Sierra Leone</option>
                    <option value="SG">Singapore</option>
                    <option value="SK">Slovakia</option>
                    <option value="SI">Slovenia</option>
                    <option value="SB">Solomon Islands</option>
                    <option value="SO">Somalia</option>
                    <option value="ZA">South Africa</option>
                    <option value="GS">
                    South Georgia and the South Sandwich Island
                    </option>
                    <option value="KR">South Korea</option>
                    <option value="SS">South Sudan</option>
                    <option value="ES">Spain</option>
                    <option value="LK">Sri Lanka</option>
                    <option value="SD">Sudan</option>
                    <option value="SR">Suriname</option>
                    <option value="SJ">Svalbard and Jan Mayen Islands</option>
                    <option value="SZ">Swaziland</option>
                    <option value="SE">Sweden</option>
                    <option value="CH">Switzerland</option>
                    <option value="TW">Taiwan</option>
                    <option value="TJ">Tajikistan</option>
                    <option value="TZ">Tanzania, United Republic of</option>
                    <option value="TH">Thailand</option>
                    <option value="TL">Timor-Leste</option>
                    <option value="TG">Togo</option>
                    <option value="TK">Tokelau</option>
                    <option value="TO">Tonga</option>
                    <option value="TT">Trinidad and Tobago</option>
                    <option value="TN">Tunisia</option>
                    <option value="TR">Turkey</option>
                    <option value="TM">Turkmenistan</option>
                    <option value="TC">Turks and Caicos Islands</option>
                    <option value="TV">Tuvalu</option>
                    <option value="UG">Uganda</option>
                    <option value="UA">Ukraine</option>
                    <option value="AE">United Arab Emirates</option>
                    <option value="GB">United Kingdom</option>
                    <option value="UM">United States Minor Outlying Islands</option>
                    <option value="UY">Uruguay</option>
                    <option value="UZ">Uzbekistan</option>
                    <option value="VU">Vanuatu</option>
                    <option value="VA">Vatican City State (Holy See)</option>
                    <option value="VE">Venezuela</option>
                    <option value="VN">Viet Nam</option>
                    <option value="VG">Virgin Islands (British)</option>
                    <option value="VI">Virgin Islands (U.S.)</option>
                    <option value="WF">Wallis and Futuna Islands</option>
                    <option value="EH">Western Sahara</option>
                    <option value="YE">Yemen</option>
                    <option value="ZM">Zambia</option>
                    <option value="ZW">Zimbabwe</option>
                </select>
            </label>

 {/* ✅ 여기부터: 카테고리 클릭 전엔 종류(체크박스) 안 보임 */}
          <section>
            <div>
              <button type="button" onClick={() => onClickCategory("allergy")}>
                allergy (Required) ({(selections.allergy ?? []).length})
              </button>

              <button type="button" onClick={() => onClickCategory("dislike")}>
                Dislike (Optional) ({(selections.dislike ?? []).length})
              </button>
            </div>

            {/* 카테고리 클릭 전엔 아무것도 안 보이게 */}
            {activeCategory ? (
              <div>
                <div>{activeCategory.label}</div>

                {activeCategory.options.map((opt) => (
                  <label key={opt.id}>
                    <input
                      type="checkbox"
                      checked={checkedList.includes(opt.id)}
                      onChange={() => toggleOption(opt.id)}
                    />
                    {opt.label}
                  </label>
                ))}
              </div>
            ) : null}

            {/* 서버로 같이 보낼 값 */}
            <input
              type="hidden"
              name="categorySelections"
              value={JSON.stringify(selections)}
            />
          </section>
        </section>

        <section>
            <button onClick={() => openModal('cancel')}>Cancel</button>
            <button onClick={() => openModal('signup')}>Sign up</button>

            <Modal
              isOpen={isModalOpen}
              onClose={() => setIsModalOpen(false)}
              onConfirm={modalType === 'cancel' ? handleCancel : handleSignup}
              message={modalType === 'cancel' ? "Are you sure you want to cancel?" : "Do you want to proceed?"}
            />
        </section>
      
    </div>
  );
}



export default SignupPage;