import "./SignupPage.css";
import Modal from "../components/Modal";
import { useMemo, useState } from "react";
import Header from "../components/Header";

function SignupPage() {
  const [formData, setformData] = useState({
    email: "",
    nickname: "",
    password: "",
    passwordConfirm: "",
    gender: "",
    country: ""
  });

  const categories = useMemo(
      () => [
          {
              id: "allergy",
              label: "allergy (Required)",
              options: Array.from({ length: 14}, (_, i) => ({
                  itemId: i +1,
                  label: `Allergy Option ${i +1}`
              })),
          },
          {
              id:"plantBased",
              label: "Plant-Based (Optional)",
              options: Array.from({ length: 2 }, (_, i) => ({
                  itemId: 100 + (i + 1),
                  label: `PlantBased Option ${i + 1}`,
              })),
          },
          {
              id:"religion",
              label: "Religion (Optional)",
              options: Array.from({ length: 4 }, (_, i) => ({
                  itemId: 200 + (i + 1),
                  label: `Religion Option ${i + 1}`,
              })),
          },          
          {
              id:"hate",
              label: "Hate (Optional)",
              options: Array.from({ length: 2 }, (_, i) => ({
                  id: `hate-${i + 1}`,
                  label: `Hate Option ${i + 1}`,
              })),
          }
      ],
      []
  );

  // 카테고리 클릭 전엔 옵션이 안 나오게: 초기값을 "" 로 둠
  const [activeCategoryId, setActiveCategoryId] = useState("");

  // 카테고리별 선택값: "optionId 문자열"이 아니라 "itemId 숫자" 배열로 유지
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

  const toggleOption = (itemId) => {
      if (!activeCategoryId) return;

      setSelections((prev) => {
      const current = prev[activeCategoryId] ?? [];
      const exists = current.includes(itemId);

      return {
          ...prev,
          [activeCategoryId]: exists
          ? current.filter((id) => id !== itemId)
          : [...current, itemId],
      };
    });
  };

 // ✅ input/select 공통 핸들러
  const onChange = (e) => {
    const { name, value } = e.target;
    setformData((prev) => ({ ...prev, [name]: value }));
  };

  // payload.item_ids 생성 (중복 제거)
  const buildItemIds = () => {
    const all = Object.values(selections).flat();
    return Array.from(new Set(all));
  };

  // hate 직접 입력용
  const [hateInput, setHateInput] = useState("");
  const [hateTags, setHateTags] = useState([]); // 최대 3개

  const addHateTag = () => {
    const v = hateInput.trim();
    if (!v) return;

    // 최대 3개
    if (hateTags.length >= 3) return;

    // 중복 방지(대소문자 무시)
    const exists = hateTags.some((t) => t.toLowerCase() === v.toLowerCase());
    if (exists) {
      setHateInput("");
      return;
    }

    setHateTags((prev) => [...prev, v]);
    setHateInput("");
  };

  const removeHateTag = (tag) => {
    setHateTags((prev) => prev.filter((t) => t !== tag));
  };


  // 백엔드 POST /members 호출
  const submitSignup = async () => {
    // 최소 검증(원하는 규칙 더 추가 가능)
    if (!formData.email || !formData.nickname || !formData.password) {
      alert("Email / Nickname / Password are required.");
      return;
    }
    if (formData.password !== formData.passwordConfirm) {
      alert("Password does not match.");
      return;
    }
    if ((selections.allergy ?? []).length === 0) {
      alert("Allergy is required.");
      return;
    }

    const payload = {
      email: formData.email,
      nickname: formData.nickname,
      password: formData.password,
      gender: formData.gender,
      country: formData.country,
      item_ids: buildItemIds(),
      hate_input: hateTags
    };

    console.log("SEND PAYLOAD:", payload);

    try {
      const res = await fetch("/members", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });

      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        // 백엔드: 409 email already exists
        alert(err?.detail ?? `Signup failed (${res.status})`);
        return;
      }

      const data = await res.json();
      console.log("Sign up success:", data);
      alert("Sign up complete!");
    } catch (e) {
      console.error(e);
      alert("Network error");
    }
  };

  //  Modal
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [modalType, setModalType] = useState(null);

  const openModal = (type) => {
    setModalType(type);
    setIsModalOpen(true);
  };

  const handleConfirm = async () => {
    if (modalType === "cancel") {
      console.log("Cancel Complete");
      setIsModalOpen(false);
      return;
    }

    // signup
    await submitSignup();
    setIsModalOpen(false);
  };

  return (
    <div className="signupPage">
      <Header showNav={false} showAuthArea={false}/>
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
                    value={formData.email}
                    onChange={onChange}
                />
            </label>

            <label>
            Nickname
                <input
                    name="nickname"
                    type="text"
                    placeholder="No more than 10 letters"
                    maxLength={10}
                    value={formData.nickname}
                    onChange={onChange}                
                />
                </label>

            <label>
            Password
                <input
                    name="password"
                    type="password"
                    placeholder="Not more than 8 to 20 letters"
                    maxLength={20}
                    value={formData.password}
                    onChange={onChange}                    
                />
                </label>

            <label>
            Password Check
                <input
                    name="passwordConfirm"
                    type="password"
                    placeholder="check password"
                    maxLength={20}
                    value={formData.passwordConfirm}
                    onChange={onChange}                    
                />
            </label>
  {/* 성별 선택창 */}
            <label>
            Gender
                <select name="gender" value={formData.gender} onChange={onChange}>
                    <option value="">choose</option>
                    <option value="Man">Man</option>
                    <option value="Woman">Woman</option>
                    <option value="Unknown">Not select</option>
                </select>
            </label>
  {/* 국가선택창 */}
            <label>
            Country
                <select name="country" value={formData.country} onChange={onChange}>
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

  {/* 여기부터: 카테고리 클릭 전엔 종류(체크박스) 안 보임 */}
          <section>
            <div>
              <button type="button" onClick={() => onClickCategory("allergy")}>
                allergy (Required) ({(selections.allergy ?? []).length})
              </button>

              <button type="button" onClick={() => onClickCategory("plantBased")}>
                Plant-based (Optional) ({(selections.plantBased ?? []).length})
              </button>
              
              <button type="button" onClick={() => onClickCategory("religion")}>
                Religion (Optional) ({(selections.religion ?? []).length})
              </button>
              
              <button type="button" onClick={() => onClickCategory("hate")}>
                Hate (Optional)
              </button>                            
            </div>

            {/* 카테고리 클릭 전엔 아무것도 안 보이게 */}
            {activeCategory ? (
              <div>
                <div>{activeCategory.label}</div>

                {/* hate 카테고리는 체크박스 대신 직접 입력 */}
                {activeCategoryId === "hate" ? (
                  <div>
                    <input
                      type="text"
                      value={hateInput}
                      placeholder="eg) coriander"
                      maxLength={50}
                      onChange={(e) => setHateInput(e.target.value)}
                      onKeyDown={(e) => {
                        if (e.key === "Enter") {
                          e.preventDefault();
                          addHateTag();
                        }
                      }}
                      disabled={hateTags.length >= 3}
                    />
                    <button
                      type="button"
                      onClick={addHateTag}
                      disabled={hateTags.length >= 3}
                    >
                      Add
                    </button>

                    {/* 태그 표시 */}
                    <div style={{ marginTop: 8, display: "flex", gap: 8, flexWrap: "wrap" }}>
                      {hateTags.map((tag) => (
                        <span
                          key={tag}
                          style={{
                            display: "inline-flex",
                            alignItems: "center",
                            gap: 6,
                            padding: "4px 8px",
                            border: "1px solid #ccc",
                            borderRadius: 999,
                            fontSize: 12,
                          }}
                        >
                          {tag}
                          <button type="button" onClick={() => removeHateTag(tag)}>
                            x
                          </button>
                        </span>
                      ))}
                    </div>

                    <div style={{ marginTop: 6, fontSize: 12 }}>
                      {hateTags.length}/3
                    </div>

                    {/* 서버로 같이 보낼 값(일단 유지용) */}
                    <input
                      type="hidden"
                      name="hateTags"
                      value={JSON.stringify(hateTags)}
                    />
                  </div>
                ) : (
                  //  기존대로 체크박스 렌더링 (hate 제외)
                  activeCategory.options.map((opt) => (
                    <label key={opt.itemId}>
                      <input
                        type="checkbox"
                        checked={checkedList.includes(opt.itemId)}
                        onChange={() => toggleOption(opt.itemId)}
                      />
                      {opt.label}
                    </label>
                  ))
                )}
              </div>
            ) : null}
          </section>
        </section>

        <section>
            <button onClick={() => openModal('cancel')}>Cancel</button>
            <button onClick={() => openModal('signup')}>Sign up</button>

            <Modal
              isOpen={isModalOpen}
              onClose={() => setIsModalOpen(false)}
              onConfirm={handleConfirm}
              message={modalType === 'cancel' ? "Are you sure you want to cancel?" : "Do you want to proceed?"}
            />
        </section>
      
    </div>
  );
}

export default SignupPage;